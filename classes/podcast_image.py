# podcast_image.py
import pillow_avif
from PIL import Image
from .utils import spinner, get_metadata_directory, log, archive_metadata, find_case_insensitive_files
from .utils import copy_file

class PodcastImage:
    def __init__(self, podcast, config):
        """
        Initialize the PodcastImage with the podcast and configuration.

        :param podcast: The podcast object containing information about the podcast.
        :param config: The configuration settings.

        The PodcastImage class is responsible for handling the podcast image file.
        """
        self.podcast = podcast
        self.config = config
        self.moved = False
        self.include_metadata = config.get('include_metadata', False)
        self.archive = config.get('archive_metadata', False)

    def get_file_path(self):
        """
        Get the path to the image file in the podcast folder.

        :return: The path to the image file in the podcast folder.
        """
        image_files = find_case_insensitive_files('*.image.*', self.podcast.folder_path)
        if not image_files:
            return None
        file_path = self.podcast.folder_path / image_files[0].name
        if not file_path.exists():
            return None
        return file_path
    
    def get_meta_file_path(self):
        """
        Get the path to the image file in the metadata directory.

        :return: The path to the image file in the metadata directory.
        """
        return get_metadata_directory(self.podcast.folder_path, self.config) / f'{self.podcast.name}.jpg'
    
    def convert_image_to_jpg(self, image_path, output_path):
        """
        Convert an image file to JPEG format.

        :param image_path: The path to the image file.
        :param output_path: The path to save the converted image.
        """
        with Image.open(image_path) as img:
            rgb_img = img.convert('RGB')
            rgb_img.save(output_path, format='JPEG')

    def resize(self):
        """
        Resize the image file to the specified size.
        """
        image_file = self.get_file_path()
        image_filename = image_file.name
        cover_size = self.config.get('cover_size', 800)
        if not image_file.suffix.lower() in [".jpg", ".jpeg"]:
            log(f"Converting image {image_filename} to JPEG", "debug")
            jpg_image_path = image_file.with_suffix('.jpg')
            self.convert_image_to_jpg(image_file, jpg_image_path)
            image_file.unlink()
            image_file = jpg_image_path
            image_filename = image_file.name
            log(f"Converted image to {jpg_image_path}", "debug")
        if image_file.exists():
            with spinner(f"Resizing image {image_filename}") as spin:
                try:
                    with Image.open(image_file) as img:
                        img.thumbnail((cover_size, cover_size))
                        img.save(self.podcast.folder_path.parent / f'{self.podcast.name}_cover.jpg', format='JPEG')
                        log(f"Resized image saved as {self.podcast.name}_cover.jpg", "debug")
                except Exception as e:
                    log("Failed to resize image", "error")
                    log(e, "debug")
                    spin.fail("✖")
                    return False
                spin.ok("✔")
                
        return image_file
    
    def archive_file(self):
        """
        Archive the image file by moving it to the metadata directory.
        """
        file_path = self.get_file_path()

        if not file_path:
            log(f"Image {file_path} does not exist.", "debug")
            return
        
        if self.archive:
            log(f"Archiving image {file_path.name}", "debug")
            archive_metadata(file_path, self.config.get('archive_metadata_directory', None))

        if not self.include_metadata:
            log(f"Deleting image {file_path.name}", "debug")        
            file_path.unlink()
            return True
        file_path = self.resize()
        if not file_path:
            return False
        if file_path.exists():
            with spinner(f"Moving image {file_path.name}") as spin:
                try:
                    file_path.rename(self.get_meta_file_path())
                    log(f"Moved image to {self.get_meta_file_path()}", "debug")
                    self.moved = True
                except Exception as e:
                    log("Failed to move image", "error")
                    log(e, "debug")
                    spin.fail("✖")
                    return False
                spin.ok("✔")
                
        return True
    
    def duplicate(self, new_folder):
        """
        Duplicate the image file to a new folder.

        :param new_folder: The folder to duplicate the image file to.
        """
        file_path = self.get_file_path()
        
        if not file_path:
            log(f"Image {file_path} does not exist - can't duplicate.", "debug")
            return
        
        new_file_path = new_folder / file_path.name
        copy_file(file_path, new_file_path)
        log(f"Duplicating image {file_path.name} to {new_file_path}", "debug")
