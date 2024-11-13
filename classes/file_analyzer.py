# file_analyzer.py
import mutagen
from collections import defaultdict
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from .utils import spinner, log

class FileAnalyzer:
    def __init__(self, podcast, config):
        """
        Initialize the FileAnalyzer with the podcast and configuration.
        
        :param podcast: The podcast object containing information about the podcast.
        :param config: The configuration settings.

        The FileAnalyzer class is responsible for analyzing the audio files in the podcast folder.
        """
        self.podcast = podcast
        self.config = config

    def analyze_files(self):
        """
        Analyze the audio files in the podcast folder.
        """
        self.earliest_year = None
        self.last_episode_date = None
        self.bitrates = defaultdict(list)
        self.file_formats = defaultdict(list)
        self.all_vbr = True
        self.durations = defaultdict(list)
        all_bad = True
        trailer_patterns = self.config.get('trailer_patterns', [])
        with spinner("Checking files") as spin:
            for file_path in self.podcast.folder_path.iterdir():
                if file_path.suffix.lower() in ['.mp3', '.m4a']:
                    metadata = self.analyze_audio_file(file_path, trailer_patterns)
                    if metadata:
                        all_bad = False
                        self.process_metadata(metadata, file_path)
            if all_bad:
                spin.fail("✖")
                log("No valid audio files found", "critical")
                return
            spin.ok("✔")

    def analyze_audio_file(self, file_path, trailer_patterns):
        """
        Analyze an individual audio file and extract metadata.
        
        :param file_path: The path to the audio file.
        :return: The metadata of the audio file.
        """
        audiofile = mutagen.File(file_path)
        if not audiofile or not hasattr(audiofile, 'info'):
            log(f"Unsupported or corrupt file, skipping: {file_path}", "warning")
            return None

        if not any(pattern.lower() in file_path.lower() for pattern in trailer_patterns):
            if isinstance(audiofile, MP3) or isinstance(audiofile, MP4):
                if audiofile.info.length:
                    self.durations[audiofile.info.length].append(file_path)

        metadata = {}
        if isinstance(audiofile, MP3):
            metadata['recording_date'] = audiofile.get("TDRC")
            metadata['bitrate'] = round(audiofile.info.bitrate / 1000)
            metadata['bitrate_mode'] = "VBR" if audiofile.info.bitrate_mode == "vbr" else "CBR"
        elif isinstance(audiofile, MP4):
            metadata['recording_date'] = audiofile.tags.get("\xa9day", [None])[0]
            metadata['bitrate'] = round(audiofile.info.bitrate / 1000)
            metadata['bitrate_mode'] = "CBR" if metadata['bitrate'] else "VBR"
        else:
            log(f"Unsupported audio format, skipping: {file_path}", "warning")
            return None
        
        if metadata['bitrate_mode'] != "VBR":
            self.all_vbr = False

        return metadata

    def process_metadata(self, metadata, file_path):
        """
        Process the metadata of an audio file.
        
        :param metadata: The metadata of the audio file.
        :param file_path: The path to the audio file.
        """
        recording_date = metadata.get('recording_date')
        if recording_date:
            year = int(str(recording_date)[:4])
            date_str = str(recording_date)
        else:
            year = None
            date_str = "Unknown"

        if self.earliest_year is None or (year and year < self.earliest_year):
            self.earliest_year = year
        if self.last_episode_date is None or date_str > self.last_episode_date:
            self.last_episode_date = date_str

        bitrate = metadata['bitrate']
        bitrate_mode = metadata['bitrate_mode']
        bitrate_str = "VBR" if "vbr" in bitrate_mode.lower() else f"{bitrate} kbps"
        self.bitrates[bitrate_str].append(file_path)

        file_format = file_path.suffix.lower()[1:]
        self.file_formats[file_format].append(file_path)

    def get_average_duration(self):
        """
        Get the average duration of the audio files.
        
        :return: The average duration in seconds.
        """
        durations = list(self.durations.keys())
        if not durations:
            return None
        return sum(durations) / len(durations)
    
    def get_longest_duration(self):
        """
        Get the longest duration of the audio files.
        
        :return: The longest duration in seconds.
        """
        durations = list(self.durations.keys())
        if not durations:
            return None
        return max(durations)
    
    def get_shortest_duration(self):
        """
        Get the shortest duration of the audio files.
        
        :return: The shortest duration in seconds.
        """
        durations = list(self.durations.keys())
        if not durations:
            return None
        return min(durations)
    
    def remove_file(self, file_path):
        """
        Remove a file from bitrates and file formats.
        
        :param file_path: The path to the file to remove.
        """
        for bitrate_list in self.bitrates.values():
            if file_path in bitrate_list:
                bitrate_list.remove(file_path)
        for format_list in self.file_formats.values():
            if file_path in format_list:
                format_list.remove(file_path)

    def update_file_path(self, old_path, new_path):
        """
        Update the file path in bitrates and file formats.
        
        :param old_path: The old path to the file.
        :param new_path: The new path to the file.
        """
        for bitrate_list in self.bitrates.values():
            if old_path in bitrate_list:
                bitrate_list.remove(old_path)
                bitrate_list.append(new_path)
        for format_list in self.file_formats.values():
            if old_path in format_list:
                format_list.remove(old_path)
                format_list.append(new_path)
