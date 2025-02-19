"""Utils for the konfuzio sdk package."""

import datetime
import hashlib
import logging
import os
import zipfile
from contextlib import contextmanager
from io import BytesIO
from typing import Union

import filetype
from PIL import Image

from konfuzio_sdk import IMAGE_FILE, PDF_FILE, OFFICE_FILE, SUPPORTED_FILE_TYPES

logger = logging.getLogger(__name__)


def get_id(a_string, include_time: bool = False) -> int:
    """
    Generate a unique ID.

    :param a_string: String used to generating the unique ID
    :param include_time: Bool to include the time in the unique ID
    :return: Unique ID
    """
    if include_time:
        unique_string = a_string + get_timestamp(format='%Y-%m-%d-%H-%M-%S.%f')
    else:
        unique_string = a_string
    try:
        return int(hashlib.md5(unique_string.encode()).hexdigest(), 16)
    except (UnicodeDecodeError, AttributeError):  # duck typing for bytes like objects
        return int(hashlib.md5(unique_string).hexdigest(), 16)


def is_file(file_path, raise_exception=True, maximum_size=100000000, allow_empty=False) -> bool:
    """
    Check if file is available or raise error if it does not exist.

    :param file_path: Path to the file to be checked
    :param raise_exception: Will raise an exception if file is not available
    :param maximum_size: Maximum size of the expected file, default < 100 mb
    :param allow_empty: Bool to allow empty files
    :return: True or false depending on the existence of the file
    """
    if os.path.isfile(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 0 or allow_empty:
            if file_size > maximum_size:
                logger.warning(f'Please check your BIG file with size {file_size / 1000000:.2f} MB at {file_path}.')
            with open(file_path, 'rb') as f:
                logger.debug(f"File expected and found at {file_path} with ID {get_id(f.read())}")
            return True
        else:
            if raise_exception:
                raise FileExistsError(f'Please check your file with size {file_size} at {file_path}.')
            else:
                return False
    else:
        if raise_exception:
            raise FileNotFoundError(f'File expected but not found at: {file_path}')
        else:
            return False


def get_timestamp(format='%Y-%m-%d-%H-%M-%S') -> str:
    """
    Return formatted timestamp.

    :param format: Format of the timestamp (e.g. year-month-day-hour-min-sec)
    :return: Timestamp
    """
    now = datetime.datetime.now()
    timestamp = now.strftime(format)
    return timestamp


def load_image(input_file: Union[str, BytesIO]):
    """
    Load an image by path or via io.Bytes, e.g. via download by URL.

    :param input_file: Path to image or image in bytes format
    :return: Loaded image
    """
    if isinstance(input_file, str):
        assert (
            get_file_type(input_file) == IMAGE_FILE
        ), 'The image file you want to load, is not defined by us as an image.'
    try:
        image = Image.open(input_file)
    except OSError:
        # in case of corrupted images
        return None

    return image


def get_file_type(input_file: Union[str, BytesIO, bytes] = None) -> str:
    """
    Get the type of a file via the filetype library, which checks the magic bytes to see the internal format.

    :param input_file: Path to the file or file in bytes format
    :return: Name of file type
    """
    if isinstance(input_file, str):
        file_name = os.path.basename(input_file)
        file_path = input_file
        extension = filetype.guess_extension(input_file)
    elif isinstance(input_file, BytesIO):
        file_name = 'BytesIO'
        file_path = 'BytesIO'
        extension = filetype.guess_extension(input_file.getvalue())
    elif isinstance(input_file, bytes):
        file_name = 'bytes'
        file_path = 'bytes'
        extension = filetype.guess_extension(input_file)
    else:
        raise NotImplementedError(f'Unsupported type of argument file: {type(input_file)}.')

    def isdir(z, name):
        """Check zip file namelist."""
        return any(x.startswith("%s/" % name.rstrip("/")) for x in z.namelist())

    file_type = None
    if extension == 'pdf':
        file_type = PDF_FILE
    elif extension in ['png', 'tiff', 'tif', 'jpeg', 'jpg']:
        file_type = IMAGE_FILE
    elif extension == 'zip':
        r = zipfile.ZipFile(input_file, "r")
        # check for office files
        if isdir(r, "docProps") or isdir(r, "_rels"):
            file_type = OFFICE_FILE

    if file_type not in [PDF_FILE, IMAGE_FILE, OFFICE_FILE]:
        error_message = f'We do not support file {file_name} with extension {extension} to get text: {file_path}'
        logger.error(error_message)
        raise NotImplementedError(error_message)

    logger.debug(f'File {file_path} is of file type {SUPPORTED_FILE_TYPES[file_type]}')
    return file_type


@contextmanager
def does_not_raise():
    """
    Serve a complement to raise, no-op context manager does_not_raise.

    docs.pytest.org/en/latest/example/parametrize.html#parametrizing-conditional-raising
    """
    yield
