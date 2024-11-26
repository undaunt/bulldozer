# podcast_metadata.py

import json
import re
from .utils import log, archive_metadata, find_case_insensitive_files, copy_file
from .data_formatter import DataFormatter
from .apis.podchaser import Podchaser
from .apis.podcastindex import Podcastindex
from .scrapers.podnews import Podnews
import feedparser

class PodcastMetadata:
    def __init__(self, podcast, config):
        """
        Initialize the PodcastMetadata with the podcast and configuration.

        :param podcast: The podcast object containing information about the podcast.
        :param config: The configuration

        The PodcastMetadata class is responsible for handling the podcast metadata.
        """
        self.podcast = podcast
        self.config = config
        self.data = {}
        self.external_data = {}
        self.has_data = False
        self.archive = config.get('archive_metadata', False)

    def load(self, search_term=None):
        """
        Load the metadata from the RSS feed or metadata file, and fetch data from the APIs.

        :param search_term: The search term to use for finding the podcast.
        :return: True if the metadata was loaded successfully, False if there was an error.
        """
        log(f"Loading metadata for {self.podcast.name}", "debug")
        if self.has_data:
            log(f"Metadata already loaded for {self.podcast.name}", "debug")
            return True

        # Attempt to parse metadata from the RSS feed
        if self.podcast.rss and self.podcast.rss.get_file_path() and self.parse_rss_feed():
            log(f"Metadata loaded from RSS feed for {self.podcast.name}", "debug")
        else:
            # Attempt to load metadata from file
            status = self.load_from_file()
            if status is None:
                log(f"Metadata file for {self.podcast.name} does not exist.", "debug")
            elif not status:
                log(f"Failed to load metadata from file for {self.podcast.name}", "error")
                return False

        # Fetch additional data from external APIs
        self.fetch_additional_data(search_term)
        self.check_if_podcast_is_complete()
        return True

    def load_from_file(self):
        """
        Load the metadata from the metadata file.

        :return: True if the metadata was loaded successfully, False if there was an error, None if the file does not exist.
        """
        file_path = self.get_file_path()
        if not file_path:
            return None  # File does not exist
        try:
            with file_path.open() as f:
                self.data = json.load(f)
                self.has_data = True
                return True
        except json.JSONDecodeError as e:
            log(f"Invalid JSON in file '{file_path.name}'. Error: {e}", "error")
            return False

    def parse_rss_feed(self):
        """
        Parse metadata from the RSS feed.

        :return: True if the metadata was parsed successfully, False otherwise.
        """
        rss_file_path = self.podcast.rss.get_file_path()
        if not rss_file_path or not rss_file_path.exists():
            log("No RSS feed file available to load metadata.", "warning")
            return False
        try:
            feed = feedparser.parse(str(rss_file_path))
            self.data['title'] = feed.feed.get('title', self.podcast.name)
            self.data['description'] = feed.feed.get('description', '')
            self.data['image'] = feed.feed.get('image', {}).get('href', '')
            self.data['link'] = feed.feed.get('link', '')
            # Add more metadata fields as needed
            self.has_data = True
            return True
        except Exception as e:
            log(f"Error parsing RSS feed for metadata: {e}", "error")
            return False

    def get_file_path(self):
        """
        Get the path to the metadata file.

        :return: The path to the metadata file.
        """
        meta_files = find_case_insensitive_files('*.meta.*', self.podcast.folder_path)
        if not meta_files:
            return None
        file_path = self.podcast.folder_path / meta_files[0].name
        if not file_path.exists():
            return None
        return file_path

    def check_if_podcast_is_complete(self):
        """
        Check if the podcast is complete based on the metadata.
        """
        if not self.external_data:
            self.podcast.completed = False
            return

        if self.external_data.get('podchaser', {}).get('status', 'ACTIVE') != 'ACTIVE':
            self.podcast.completed = True
            return

        self.podcast.completed = False

    def format_data(self):
        """
        Format the metadata data using the DataFormatter.
        """
        formatter = DataFormatter(self.config)
        self.data = formatter.format_data(self.data)
        self.external_data = formatter.format_data(self.external_data)

    def fetch_additional_data(self, search_term=None):
        """
        Fetch additional metadata from APIs.
        """
        self.get_podchaser_data(search_term)
        self.get_podcastindex_data(search_term)
        self.get_podnews_data(search_term)
        self.format_data()

    def replace_description(self, description):
        """
        Replace parts of the description based on the configuration.

        :param description: The description to replace parts of.
        :return: The description with replacements made.
        """
        replacements = self.config.get('description_replacements', [])
        for replacement in replacements:
            pattern = replacement['pattern']
            repl = replacement['replace_with']
            escaped_pattern = re.escape(pattern)
            description = re.sub(escaped_pattern, repl, description)
        return description.strip()

    def get_description(self):
        """
        Get the description from the metadata.

        :return: The description from the metadata.
        """
        if not self.data:
            return None

        description = self.data.get('description')
        if not description:
            return None

        return self.replace_description(description)

    def get_links(self):
        """
        Get the links from the metadata.

        :return: The links from the metadata.
        """
        if not self.data:
            return None

        links = {}
        if 'link' in self.data and self.data['link']:
            links['Official Website'] = self.data['link'].strip()
        if 'podnews' in self.external_data and 'url' in self.external_data['podnews']:
            links['Podnews'] = self.external_data['podnews']['url']
        if 'podcastindex' in self.external_data and 'url' in self.external_data['podcastindex']:
            links['Podcastindex.org'] = self.external_data['podcastindex']['url']

        return links

    def get_tags(self):
        """
        Get the tags from the metadata.

        :return: The tags from the metadata.
        """
        if not self.data:
            return None

        tags = []
        if 'categories' in self.data:
            categories = self.data['categories']
            for category in categories:
                tags.append(category.strip().lower())
        if 'itunes' in self.data and 'categories' in self.data['itunes']:
            itunes_categories = self.data['itunes']['categories']
            for category in itunes_categories:
                tags.append(category.strip().lower())
        if 'explicit' in self.data.get('itunes', {}):
            if self.data['itunes']['explicit'] == 'yes':
                tags.append('explicit')

        return ', '.join(set(tags))

    def get_rss_feed(self):
        """
        Get the RSS feed URL from the metadata.

        :return: The RSS feed URL from the metadata.
        """
        if not self.data:
            return None

        return self.data.get('feedUrl', None)

    def get_external_data(self, api_name, api_class, search_term, *args):
        """
        Get the data for the podcast from a specified API.

        :param api_name: Name of the API (e.g., 'podchaser', 'podcastindex').
        :param api_class: The class for interacting with the API (e.g., Podchaser, Podcastindex).
        :param search_term: The search term to use for finding the podcast.
        :param args: Additional arguments required for the API class constructor.
        """
        api_config = self.config.get(api_name, {})
        log(f"Getting {api_name.capitalize()} data for {self.podcast.name}", "debug")

        if not api_config.get('active', False):
            log(f"{api_name.capitalize()} API is not enabled.", "debug")
            return None

        if not search_term:
            search_term = self.podcast.name

        api_instance = api_class(*args)
        podcast = api_instance.find_podcast(search_term)

        if not podcast:
            self.external_data[api_name] = {}
            return False

        self.external_data[api_name] = podcast
        self.has_data = True
        return True

    def get_podchaser_data(self, search_term=None):
        """
        Get the Podchaser data for the podcast.

        :param search_term: The search term to use for finding the podcast.
        """
        return self.get_external_data(
            'podchaser',
            Podchaser,
            search_term,
            self.config.get('podchaser', {}).get('token', None),
            self.config.get('podchaser', {}).get('fields', None),
            self.config.get('podchaser', {}).get('url', None)
        )

    def get_podcastindex_data(self, search_term=None):
        """
        Get the Podcast Index data for the podcast.

        :param search_term: The search term to use for finding the podcast.
        """
        return self.get_external_data(
            'podcastindex',
            Podcastindex,
            search_term,
            self.config.get('podcastindex', {}).get('key', None),
            self.config.get('podcastindex', {}).get('secret', None),
            self.config.get('podcastindex', {}).get('url', None)
        )

    def get_podnews_data(self, search_term=None):
        """
        Get the Podnews data for the podcast.

        :param search_term: The search term to use for finding the podcast.
        """
        return self.get_external_data(
            'podnews',
            Podnews,
            search_term,
            self.config.get('podnews', {}).get('url', None)
        )

    def archive_file(self):
        """
        Archive the metadata file.

        If the archive_metadata configuration is set to True, the metadata file will be archived instead of deleted.
        """
        file_path = self.get_file_path()

        if not file_path:
            log("Metadata file does not exist.", "debug")
            return

        if not self.archive:
            log(f"Deleting metadata file {file_path.name}", "debug")
            file_path.unlink()
            return

        archive_folder = self.config.get('archive_metadata_directory', None)
        archive_metadata(file_path, archive_folder)
        log(f"Archived metadata file {file_path.name}", "debug")
        file_path.unlink()

    def duplicate(self, new_folder):
        """
        Duplicate the metadata file to a new folder.

        :param new_folder: The folder to duplicate the metadata file to.
        """
        file_path = self.get_file_path()

        if not file_path:
            log("Metadata file does not exist - can't duplicate.", "debug")
            return

        new_file_path = new_folder / file_path.name
        copy_file(file_path, new_file_path)
        log(f"Duplicated metadata file {file_path.name} to {new_file_path}", "debug")

    def get_external_ids(self):
        """
        Get external IDs from the external data sources.

        :return: List of external IDs.
        """
        ids = []
        for dataset in self.external_data.values():
            ids.append(dataset.get('id'))
        return ids
