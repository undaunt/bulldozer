# podcast.py
import shutil
from .file_organizer import FileOrganizer
from .file_analyzer import FileAnalyzer
from .dupe_checker import DupeChecker
from .rss import Rss
from .podcast_image import PodcastImage
from .podcast_metadata import PodcastMetadata
from .utils import log, run_command, announce, spinner, get_metadata_directory

class Podcast:
    def __init__(self, name, folder_path, config, source_rss_file=None, censor_rss=False, check_duplicates=True, search_term=None):
        """
        Initialize the Podcast with the name, folder path, configuration, and source RSS file.

        :param name: The name of the podcast.
        :param folder_path: The path to the podcast folder.
        :param config: The configuration settings.
        :param source_rss_file: The source RSS file to download.
        :param censor_rss: If True, the RSS feed will be censored.
        :param check_duplicates: If True, check for duplicate episodes.
        :param search_term: The search term used to find the podcast.

        The Podcast class is responsible for handling the podcast.
        """
        self.name = name
        if '(' in self.name:
            self.name = self.name.split('(')[0].strip()
        self.folder_path = folder_path
        self.config = config
        self.completed = False
        self.downloaded = False
        if self.name != 'unknown podcast':
            self.downloaded = True
        self.search_term = search_term
        self.rss = Rss(self, source_rss_file, self.config, censor_rss)
        self.image = PodcastImage(self, self.config)
        self.metadata = PodcastMetadata(self, self.config)
        self.analyzer = FileAnalyzer(self, config)
        if self.name != 'unknown podcast' and check_duplicates:
            self.check_for_duplicates()

    def download_episodes(self):
        """
        Download the podcast episodes using podcast-dl.

        :param episode_template: The template for the episode file names.
        :param threads: The number of threads to use for downloading.
        """
        metadata = self.rss.get_metadata()

        if not metadata:
            announce("Failed to get metadata from RSS feed", "critical")
            exit(1)

        self.name = self.rss.metadata['name']

        self.check_for_duplicates()

        episode_template = self.config.get("podcast_dl", {}).get('episode_template', "{{podcast_title}} - {{release_year}}-{{release_month}}-{{release_day}} {{title}}")
        threads = self.config.get("podcast_dl", {}).get("threads", 1)

        command = (
            f'podcast-dl --file "{self.rss.get_file_path()}" --out-dir "{self.folder_path}" '
            f'--episode-template "{episode_template}" '
            f'--include-meta --threads {threads} --add-mp3-metadata'
        )
        download_output, return_code = run_command(command, progress_description="Downloading podcast episodes", track_progress=True, total_episodes=self.rss.metadata['total_episodes'])
        if return_code != 0:
            log("Failed to download episodes using podcast-dl.", "error")
            log(download_output, "debug")
            exit(1)

    def organize_files(self):
        """
        Organize the podcast files.
        """
        organizer = FileOrganizer(self, self.config)
        organizer.organize_files()

    def analyze_files(self):
        """
        Analyze the podcast files.
        """
        self.analyzer.analyze_files()

    def check_for_duplicates(self):
        """
        Check for duplicate episodes.

        :return: True if there are no duplicates, False otherwise.
        """
        if self.config.get('api_key') and self.config.get('dupecheck_url'):
            term = self.search_term if self.search_term else self.name
            dupe_checker = DupeChecker(term, self.config.get('dupecheck_url'), self.config.get('api_key'))
            progress = dupe_checker.check_duplicates()
            if not progress:
                self.cleanup_and_exit()
        else:
            log("Skipping duplicate check because 'api_key' or 'dupecheck_url' is not set in the config.", "debug")

    def archive_files(self):
        """
        Archive the podcast files.
        """
        with spinner("Organizing metadata files") as spin:
            self.metadata.archive_file()
            self.image.archive_file()
            self.rss.archive_file()
            if not self.config.get('include_metadata', False):
                metadata_directory = get_metadata_directory(self.folder_path, self.config)
                if metadata_directory.exists():
                    metadata_directory.rmdir()
            spin.ok("✔")

    def cleanup_and_exit(self):
        """
        Clean up and exit.
        """
        log("Cleaning up and exiting...", "debug")
        shutil.rmtree(self.folder_path)
        exit(1)
