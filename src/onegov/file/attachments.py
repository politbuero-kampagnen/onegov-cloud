import pdftotext

from depot.fields.upload import UploadedFile
from depot.io import utils
from depot.io.interfaces import FileStorage
from depot.io.utils import INMEMORY_FILESIZE
from io import BytesIO
from onegov.core.html import sanitize_svg
from onegov.file.utils import digest
from onegov.file.utils import get_image_size
from onegov.file.utils import get_svg_size
from onegov.file.utils import IMAGE_MIME_TYPES
from onegov.file.utils import word_count
from PIL import Image
from tempfile import SpooledTemporaryFile
from onegov.pdf.utils import extract_pdf_info


IMAGE_MAX_SIZE = 2048
IMAGE_QUALITY = 85
CHECKSUM_FUNCTION = 'md5'


def get_svg_size_or_default(content):
    width, height = get_svg_size(content)

    width = width if width is not None else '{}px'.format(IMAGE_MAX_SIZE)
    height = height if height is not None else '{}px'.format(IMAGE_MAX_SIZE)

    return width, height


def limit_and_store_image_size(file, content, content_type):

    if content_type == 'image/svg+xml':
        file.size = get_svg_size_or_default(content)

    if content_type not in IMAGE_MIME_TYPES:
        return None

    image = Image.open(content)

    if max(image.size) > IMAGE_MAX_SIZE:
        image.thumbnail((IMAGE_MAX_SIZE, IMAGE_MAX_SIZE), Image.LANCZOS)
        content = SpooledTemporaryFile(INMEMORY_FILESIZE)
        try:
            # Quality is only supported by jpeg
            image.save(content, image.format, quality=IMAGE_QUALITY)
        except ValueError:
            image.save(content, image.format)

    # the file size is stored in pixel as string (for browser usage)
    file.size = get_image_size(image)

    return content


def calculate_checksum(content):
    return digest(content, type=CHECKSUM_FUNCTION)


def store_checksum(file, content, content_type):
    file.checksum = calculate_checksum(content)


def sanitize_svg_images(file, content, content_type):
    if content_type == 'image/svg+xml':
        sane_svg = sanitize_svg(content.read().decode('utf-8'))
        content = BytesIO(sane_svg.encode('utf-8'))

    return content


def store_extract_and_pages(file, content, content_type):
    if content_type == 'application/pdf':
        pages, file.extract = extract_pdf_info(content)

        file.stats = {
            'pages': pages,
            'words': word_count(file.extract)
        }


class ProcessedUploadedFile(UploadedFile):

    processors = (
        store_checksum,
        limit_and_store_image_size,
        sanitize_svg_images,
        store_extract_and_pages,
    )

    def process_content(self, content, filename=None, content_type=None):
        filename, content_type = FileStorage.fileinfo(content)[1:]
        content = utils.file_from_content(content)

        try:
            for processor in self.processors:
                content = processor(self, content, content_type) or content
                content.seek(0)
        except Image.DecompressionBombError:
            # not a real content type - but useful for us to be able to rely
            # on anything uploaded having a content type, even though that
            # content is discarded soon afterwards
            content = b''
            content_type = 'application/malicious'
        except pdftotext.Error:
            # signed pdfs have shown to be difficult to handle by pdftotext
            # it uses poppler apt package in the background resulting in old
            # versions installed on the host. We still would like to sign
            # the pdfs in which case file.stats has hopefully been set already
            pass

        super().process_content(content, filename, content_type)
