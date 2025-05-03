import json
import os
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator
from PIL import Image
import piexif
import tifffile


@contextmanager
def open_image(image_path: str) -> Generator[Image.Image, None, None]:
    """
    Context manager for opening image and ensuring they're properly closed.

    Args:
        image_path (str): Path to the image file

    Yields:
        Image.Image: The opened image object
    """
    img = None
    try:
        img = Image.open(image_path)
        yield img
    finally:
        if img is not None and hasattr(img, "close"):
            img.close()


def embed_metadata(image_path: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Embed metadata in image (PNG, TIFF, TIF, JPEG, JPG)

    Args:
        image_path (str): Path of the input image
        metadata (dict, optional): Metadata to add in image

    Returns:
        bool: True if metadata was successfully embedded, False otherwise
    """
    if not metadata:
        print("No metadata provided for embedding")
        return False

    file_ext = os.path.splitext(image_path.lower())[1]

    try:
        metadata_str = json.dumps(metadata)
        if file_ext in (".png", ".jpg", ".jpeg"):
            with open_image(image_path) as image:
                exif_dict = {
                    "0th": {},
                    "Exif": {piexif.ExifIFD.UserComment: metadata_str.encode()},
                    "GPS": {},
                    "1st": {},
                    "thumbnail": None,
                }
                exif_bytes = piexif.dump(exif_dict)
                image.save(image_path, exif=exif_bytes)

        elif file_ext in (".tif", ".tiff"):
            # For TIFF files, we need to read the existing data and then rewrite with metadata
            with tifffile.TiffFile(image_path) as tiff:
                image_data = tiff.asarray()

            tifffile.imwrite(
                image_path,
                image_data,
                description=metadata_str,  # This properly sets the ImageDescription tag
                metadata=None,  # Don't use the metadata parameter as it doesn't work as expected
            )

        else:
            print(f"Unsupported file format: {file_ext}")
            return False

        print(f"Successfully embedded metadata in {image_path}")
        return True

    except Exception as e:
        print(f"Error embedding metadata in {image_path}: {e}")
        return False


def read_metadata(image_path: str) -> Optional[Dict[str, Any]]:
    """
    Read and extract metadata from an image file.

    Args:
        image_path (str): Path of the image file

    Returns:
        Optional[Dict[str, Any]]: Extracted metadata information from image or None if error
    """
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return None

    file_ext = os.path.splitext(image_path.lower())[1]

    try:
        metadata = {
            "basic_info": {
                "format": None,
                "size": None,
                "mode": None,
            },
            "metadata_info": None,
        }

        with open_image(image_path) as image:
            metadata["basic_info"] = {
                "format": image.format,
                "size": image.size,
                "mode": image.mode,
            }

            if file_ext in (".png", ".jpeg", ".jpg"):
                if "exif" in image.info:
                    exif_dict = piexif.load(image.info.get("exif", b""))
                    if (
                        "Exif" in exif_dict
                        and piexif.ExifIFD.UserComment in exif_dict["Exif"]
                    ):
                        user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
                        if isinstance(user_comment, bytes):
                            json_str = user_comment.decode("utf-8")
                            try:
                                metadata["metadata_info"] = json.loads(json_str)
                            except json.JSONDecodeError:
                                print(f"Invalid JSON in metadata: {json_str}")
                                metadata["metadata_info"] = user_comment
                        else:
                            metadata["metadata_info"] = user_comment
                    else:
                        print("No UserComment found in EXIF data")
                else:
                    print("No EXIF data found in image")

        # Process TIFF files separately since we need to close the PIL image before opening with tifffile
        if file_ext in (".tif", ".tiff"):
            with tifffile.TiffFile(image_path) as tiff:
                if hasattr(tiff, "pages") and tiff.pages:
                    # Get the first page's tags
                    first_page = tiff.pages[0]
                    if 270 in first_page.tags:  # type: ignore # 270 is the ImageDescription tag ID
                        description = first_page.tags[270].value  # type: ignore
                        try:
                            metadata["metadata_info"] = json.loads(description)
                        except json.JSONDecodeError:
                            print(
                                f"Invalid JSON in TIFF ImageDescription: {description}"
                            )
                            metadata["metadata_info"] = description
                    else:
                        print("No ImageDescription tag found in TIFF file")

        return metadata

    except Exception as e:
        print(f"Error reading metadata from {image_path}: {e}")
        return None


def process_directory(directory: str, file_extension: str) -> None:
    """
    Process all images in a directory to embed or read metadata.

    Args:
        directory (str): Directory containing images
        file_extension (str, optional): Filter for specific file extensions
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist")
        return

    metadata = {
        "author": "rjoydip",
        "timestamp": "2023-04-15T12:00:00",
        "description": "Metadata embedded using improved script",
    }

    for root, _, files in os.walk(directory):
        print(f"Processing directory: {root}")

        # Process files that match the extension filter
        for file in files:
            if file_extension and not file.lower().endswith(file_extension):
                continue

            image_path = os.path.join(root, file)

            # Embed metadata
            print(f"Embedding metadata in {file}")
            success = embed_metadata(image_path, metadata)

            if success:
                # Read metadata to verify
                print(f"Reading metadata from {file}")
                result = read_metadata(image_path)
                if result:
                    print(f"Metadata for {file}:\n{json.dumps(result, indent=2)}")
                else:
                    print(f"Failed to read metadata from {file}")


def main() -> None:
    """Main function to process images in the artifacts directory."""
    try:
        filter_file_extension = ".tif"
        directory = os.path.join(os.getcwd(), "artifacts")

        print(
            f"Starting metadata processing for {filter_file_extension} files in {directory}"
        )
        process_directory(directory, filter_file_extension)
        print("Metadata processing completed")

    except Exception as e:
        print(f"Unexpected error in main function: {e}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time
    print(f"Execution took {elapsed_time:.2f} seconds")
