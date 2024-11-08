# file_organizer.py
import fnmatch
import re
from datetime import datetime, timedelta
from pathlib import Path
from .utils import spinner, titlecase_filename, announce, log
from .utils import format_last_date, ask_yes_no, take_input

class FileOrganizer:
    def __init__(self, podcast, config):
        """
        Initialize the FileOrganizer with the podcast and configuration.
        
        :param podcast: The podcast object containing information about the podcast.
        :param config: The configuration settings.

        The FileOrganizer class is responsible for organizing the episode files in the podcast folder.
        """
        self.podcast = podcast
        self.config = config
        self.unwanted_files = self.config.get('unwanted_files', [])

    def rename_files(self):
        """
        Rename the episode files in the podcast folder.
        """
        ep_nr_at_end_file_pattern = re.compile(self.config.get('ep_nr_at_end_file_pattern', r'^(.* - )(\d{4}-\d{2}-\d{2}) (.*?)( - )(\d+)\.mp3$'))
        for file_path in Path(self.podcast.folder_path).rglob('*'):
            if file_path.is_file():
                self.rename_file(file_path, ep_nr_at_end_file_pattern)

    def get_new_name(self, name, file_path):
        """
        Get the new name for the file by applying the file replacements.

        :param name: The original name of the file.
        :param file_path: The path to the file.
        :return: The new name of the file.
        """
        for item in self.config.get('file_replacements', []):
            pattern = item['pattern']
            replacement = item['replacement']
            flags = item.get('flags', [])
            regex_flags = 0
            flag_mapping = {
                'IGNORECASE': re.IGNORECASE,
                'MULTILINE': re.MULTILINE,
                'DOTALL': re.DOTALL,
                'VERBOSE': re.VERBOSE,
                'ASCII': re.ASCII,
            }
            for flag in flags:
                regex_flags |= flag_mapping.get(flag.upper(), 0)

            repeat = item.get('repeat_until_no_change', False)

            if repeat:
                previous_name = None
                while previous_name != name:
                    previous_name = name
                    name = re.sub(pattern, replacement, name)
            else:
                name = re.sub(pattern, replacement, name)

        log(f"Renaming '{file_path.name}' to '{name}'", "debug")

        return file_path.with_name(name)
    
    def fix_episode_numbering(self, file_path, ep_nr_at_end_file_pattern):
        """
        Fix the episode numbering in the file name.

        :param file_path: The path to the file.
        :param ep_nr_at_end_file_pattern: The pattern to match episode numbers at the end of the file name.
        """
        match = ep_nr_at_end_file_pattern.match(file_path.name)
        if match:
            prefix = match.group(1)
            date_part = match.group(2)
            title = match.group(3).rstrip(' -').strip()
            last_number = match.group(5)
            extension = match.group(6)
            
            new_filename = f"{prefix}{date_part} {last_number}. {title}{extension}"
            new_path = file_path.with_name(new_filename)
            file_path.rename(new_path)
            file_path = new_path

        return file_path

    def rename_file(self, file_path, ep_nr_at_end_file_pattern):
        """
        Rename an individual episode file.

        :param file_path: The path to the file.
        :param ep_nr_at_end_file_pattern: The pattern to match episode numbers at the end of the file name.
        """
        new_name = titlecase_filename(file_path, self.config)

        new_path = self.get_new_name(new_name, file_path)
        file_path.rename(new_path)
        file_path = new_path

        self.fix_episode_numbering(file_path, ep_nr_at_end_file_pattern)

    def find_unwanted_files(self):
        """
        Find and remove unwanted files from the podcast folder.
        """
        announce("Checking if there are episodes we don't want", "info")
        for file_path in Path(self.podcast.folder_path).rglob('*'):
            if file_path.is_file() and any(unwanted_file.lower() in file_path.name.lower() for unwanted_file in self.unwanted_files):
                if ask_yes_no(f"Would you like to remove '{file_path.name}'"):
                    file_path.unlink()

    def pad_episode_numbers(self):
        """
        Pad episode numbers with zeros to make them consistent
        """
        # Define the pattern for matching episode numbers
        pattern = re.compile(self.config.get('episode_pad_pattern', r'(Ep\.?|Episode)\s*(\d+)'), re.IGNORECASE)

        files_with_episodes = []

        # Collect files with episode numbers
        for filename in Path(self.podcast.folder_path).rglob('*'):
            match = pattern.search(filename.name)
            if match:
                episode_number = int(match.group(2))
                files_with_episodes.append((filename, episode_number))

        if not files_with_episodes:
            log("No files with episode numbers found", "debug")
            return

        # Determine the padding length
        max_episode_number = max(ep_num for _, ep_num in files_with_episodes)
        num_digits = len(str(max_episode_number))

        # Function to replace episode number with padded version
        def pad_episode_number(match):
            prefix = match.group(1)  # The "Ep", "Ep.", or "Episode" part
            episode_number = int(match.group(2))  # The numeric part
            padded_episode = str(episode_number).zfill(num_digits)  # Pad the number based on the required length
            return f"{prefix} {padded_episode}"

        for filename, _ in files_with_episodes:
            new_filename = pattern.sub(pad_episode_number, filename.name)
            new_path = filename.with_name(new_filename)

            filename.rename(new_path)
            log(f"Renamed '{filename}' to '{new_path}'", "debug")

    def check_numbering(self):
        """
        Check if episode numbers are present and consistent in the file names.
        """
        announce("Checking if episode numbers are present and consistent", "info")
        self.pad_episode_numbers()
        pattern = re.compile(self.config.get('numbered_episode_pattern', r'^(.* - )(\d{4}-\d{2}-\d{2}) (\d+)\. (.*)(\.\w+)'))
    
        files = Path(self.podcast.folder_path).rglob('*')
        has_episode_number = any(pattern.match(f.name) for f in files)
        
        if has_episode_number:
                
            missing_episode_number = [f for f in files if not pattern.match(f.name)]
            
            if missing_episode_number:
                for f in missing_episode_number:
                    if (f.is_file() and not fnmatch.fnmatch(f.name, '*.mp3') and not fnmatch.fnmatch(f.name, '*.m4a')) or not f.is_file():
                        continue
                    episode_number = take_input(f"Episode number for '{f}' (blank skips)")
                    if episode_number:
                        original_pattern = re.compile(self.config.get('numbered_episode_pattern', r'^(.*) - (\d{4}-\d{2}-\d{2}) (.*?)(\.\w+)'))
                        match = original_pattern.match(f.name)
                        
                        if match:
                            prefix = match.group(1)
                            date_part = match.group(2)
                            title = match.group(3).strip()
                            extension = match.group(4)

                            new_filename = f"{prefix} - {date_part} {episode_number}. {title}{extension}"

                            folder_path = Path(folder_path)

                            old_filepath = folder_path / f
                            new_filepath = folder_path / new_filename

                            old_filepath.rename(new_filepath)

    def organize_files(self):
        """
        Organize the episode files in the podcast folder.
        """
        self.rename_folder()
        with spinner("Organizing episode files") as spin:
            self.rename_files()
            spin.ok("✔")

        self.find_unwanted_files()
        self.check_numbering()

    def rename_folder(self):
        """
        Rename the podcast folder based on the podcast name and last episode date.
        """
        if '(' in self.podcast.folder_path.name:
            return
        date_format_short = self.config.get('date_format_short', '%Y-%m-%d')
        date_format_long = self.config.get('date_format_long', '%B %d %Y')
        start_year_str = str(self.podcast.analyzer.earliest_year) if self.podcast.analyzer.earliest_year else "Unknown"
        last_episode_date_str = format_last_date(self.podcast.analyzer.last_episode_date, date_format_long) if self.podcast.analyzer.last_episode_date else "Unknown"
        last_episode_date_dt = datetime.strptime(self.podcast.analyzer.last_episode_date, date_format_short) if self.podcast.analyzer.last_episode_date != "Unknown" else None
        new_folder_name = None
        if last_episode_date_dt and datetime.now() - last_episode_date_dt > timedelta(days=self.config.get('completed_threshold_days', 365)):
            if ask_yes_no(f'Would you like to rename the folder to {self.podcast.name} (Complete)'):
                new_folder_name = f"{self.podcast.name} (Complete)"
                self.podcast.completed = True
        if not new_folder_name:
            if ask_yes_no(f'Would you like to rename the folder to {self.podcast.name} ({start_year_str}-{last_episode_date_str})'):
                new_folder_name = f"{self.podcast.name} ({start_year_str}-{last_episode_date_str})"
        if not new_folder_name:
            new_folder_name = take_input(f'Enter a custom name for the folder (blank skips)')

        if new_folder_name:
            new_folder_path = self.podcast.folder_path.parent / new_folder_name
            log(f"Renaming folder {self.podcast.folder_path} to {new_folder_path}", "debug")
            self.podcast.folder_path.rename(new_folder_path)
            self.podcast.folder_path = new_folder_path
        
        return
