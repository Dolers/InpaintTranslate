"""Interfaces for text detection."""
from absl import logging
from dataclasses import dataclass
from typing import Sequence
from PIL import Image

import pytesseract
import time

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

from paddleocr import PaddleOCR

@dataclass
class TextBox:
  # (x, y) is the top left corner of a rectangle; the origin of the coordinate system is the top-left of the image.
  # x denotes the horizontal axis, y denotes the vertial axis
  x: int
  y: int
  w: int
  h: int
  text: str = None
  lines: int = 1
  
  @staticmethod
  def from_grouped_boxes(group: Sequence['TextBox']) -> 'TextBox':
    
    return TextBox( x = min(group, key=lambda box: box.x).x,
                    y = group[0].y,
                    w = max(group, key=lambda box: box.w).w,
                    h = group[-1].y + group[-1].h -group[0].y,
                    text  = " ".join(box.text for box in group),
                    lines = len(group))


class TextDetector:
  def detect_text(self, image_filename: str) -> Sequence[TextBox]:
    pass


class AzureTextDetector(TextDetector):
  """Calls the Computer Vision endpoint from Microsoft Azure. Promises to work with images in the wild."""

  def __init__(self, endpoint, key):
    self.client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

  def detect_text(self, image_filename: str) -> Sequence[TextBox]:
    read_response = self.client.read_in_stream(open(image_filename, "rb"), raw=True)

    # Get the operation location (URL with an ID at the end) from the response
    read_operation_location = read_response.headers["Operation-Location"]
    # Grab the ID from the URL
    operation_id = read_operation_location.split("/")[-1]

    # Call the "GET" API and wait for it to retrieve the results
    while True:
      read_result = self.client.get_read_result(operation_id)
      if read_result.status not in ['notStarted', 'running']:
        break
      time.sleep(1)

    text_boxes = []
    if read_result.status == OperationStatusCodes.succeeded:
      for text_result in read_result.analyze_result.read_results:
        for line in text_result.lines:
          # line.bounding_box contains the 4 corners of a polygon (not necessarily a rectangle).
          # To keep things simple, we turn them into rectangles. There are two ways: (1) use the rectangle
          # defined by the top-left and bottom-right corners, or (2) use the rectangle that encompasses the
          # entire polygon. (1) will lead to smaller surfaces, (2) to bigger surfaces.

          # Implementation for (1)
          # tl_x, tl_y = line.bounding_box[0:2]   # top left
          # br_x, br_y = line.bounding_box[4:6]   # bottom right
          # w = br_x - tl_x
          # h = br_y - tl_y

          # Implementation for (2)
          xs = [point for idx, point in enumerate(line.bounding_box) if idx % 2 == 0]
          ys = [point for idx, point in enumerate(line.bounding_box) if idx % 2 == 1]
          tl_x = min(xs)
          tl_y = min(ys)
          h = max(xs) - tl_x
          w = max(ys) - tl_y

          if h < 0 or w < 0:
            logging.error(f"Malformed bounding box from Azure: {line.bounding_box}")

          text_boxes.append(TextBox(int(tl_x), int(tl_y), int(w), int(h), line.text))
    return text_boxes


class TesseractTextDetector(TextDetector):
  """Uses the `tesseract` OCR library from Google to do text detection."""

  def __init__(self, tesseract_path: str):
    """
    Args:
      tesseract_path: The path where the `tesseract` library is installed, e.g. "/usr/bin/tesseract".
    """
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

  def detect_text(self, image_filename: str) -> Sequence[TextBox]:
    image = Image.open(image_filename)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    boxes = [TextBox(l, top, w, h, text)
             for l, top, w, h, text in zip(data["left"], data["top"], data["width"], data["height"], data["text"])
             if text.strip()]
    return boxes


class PaddleTextDetector(TextDetector):

  def __init__(self, pad_size: int = 10):
     self.ocr = PaddleOCR(use_angle_cls=False, lang='en')
     self.pad_size =  pad_size
     
  def detect_text(self, image_filename: str) -> Sequence[TextBox]:
    result = self.ocr.ocr(image_filename, cls=False)
    return [TextBox(line[0][0][0]-self.pad_size,
                    line[0][0][1]-self.pad_size,
                    line[0][2][0]-line[0][0][0]+self.pad_size*2,
                    line[0][2][1]-line[0][0][1]+self.pad_size*2,
                    line[1][0])
             for line in result[0] if '©' not in line[1][0]]
