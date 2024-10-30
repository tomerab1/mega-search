import asyncio
from PIL import Image
from spire.doc import *
from spire.doc.common import *
import pytesseract
import pdf2image


class FileProcessor:
    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    # path = '/home/tomerab/mega-search/backend/fileprocessor/CS/04101 - אשנב למתמטיקה/Lessons/Presentations/מצגת שיעור 1.pdf'
    # img = pdf2image.convert_from_path(path)

    # all_text = ""
    # for i, image in enumerate(img):
    #     text = pytesseract.image_to_string(image, lang='heb+eng')
    #     all_text += text

    # print(all_text)

    # path = '/home/tomerab/mega-search/backend/fileprocessor/CS/04101 - אשנב למתמטיקה/Mamans/2008c/01-mmn-11_0.doc'
    # doc = Document()
    # doc.LoadFromFile(path)

    # print(doc.GetText())
