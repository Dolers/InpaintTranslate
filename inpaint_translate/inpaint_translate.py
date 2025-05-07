from inpaint_translate.logger_config import get_logger
import os
from pathlib import Path
from inpaint_translate.inpainter import Inpainter
from inpaint_translate.text_detector import TextDetector, TextBox
from PIL import ImageDraw, Image
from deep_translator.base import BaseTranslator

from inpaint_translate.text_draw import draw_text_boxes_on_image
import json
from shutil import copyfile

logger = get_logger()


class InpaintTranslator:
    def __init__(
        self,
        text_detector: TextDetector,
        inpainter: Inpainter,
        translator: BaseTranslator,
    ):
        self.text_detector = text_detector
        self.inpainter = inpainter
        self.translator = translator

    def inpaint_translate(
        self,
        in_image: Path,
        out_image: Path,
        max_retries: int,
        prompt=Inpainter.DEFAULT_PROMPT,
    ):
        """
        Removes text from an input image by iteratively applying an inpainting process.
        Use this if the inpainter is not able to remove all text in one go.
        Args:
          in_image (Path): The path to the input image file to be processed.
          out_image (Path): The path where the output image file will be saved.
          max_retries (int): The maximum number of iterations to attempt for inpainting.
          prompt (str, optional): The inpainting prompt to guide the process. Defaults to Inpainter.DEFAULT_PROMPT.
        Raises:
          AssertionError: If the output image file does not exist after processing.
        """
        to_inpaint_path = in_image
        for i in range(max_retries + 1):
            logger.info(f"Iteration {i} of {max_retries} for image {in_image}:")

            self.inpaint_translate(to_inpaint_path, out_image, prompt)

            assert os.path.exists(out_image)
            to_inpaint_path = out_image

    def inpaint_translate(
        self, in_image: Path, out_image: Path, prompt=Inpainter.DEFAULT_PROMPT
    ):
        """
        Processes an input image to translate the text in it.
        This method performs the following steps:
        1. Detects text regions in the input image using a text detection model.
        2. Removes the detected text regions using an inpainting model.
        3. Groups the detected text boxes for translation.
        4. Translates the text in each grouped box using a translation model.
        5. Draws the translated text back onto the output image.
        Args:
          in_image (Path): The path to the input image file.
          out_image (Path): The path to save the output image file.
          prompt (str, optional): The inpainting prompt to guide the inpainting model.
        Raises:
          Any exceptions raised by the text detection, inpainting, or translation
          models will propagate to the caller.
        Notes:
          - Debug visualizations are saved if the logger level is set to DEBUG.
        """

        logger.info(f"Calling text detector...")
        text_boxes = self.text_detector.detect_text(in_image.__str__())
        logger.info(f"\tDetected {len(text_boxes)} text boxes.")
        logger.debug(json.dumps([box.__dict__ for box in text_boxes], indent=2))

        if not text_boxes:
            logger.warning(f"No text boxes detected!")
            return

        self._debug_draw_text_boxes(in_image, text_boxes, "_textboxes")

        logger.info(f"Calling in-painting model...")
        self.inpainter.inpaint(in_image, text_boxes, prompt, out_image)
        if logger.level >= 10: # fuck python logging
            copyfile(out_image, f"debug/{in_image.stem}_inpainted{in_image.suffix}")

        logger.info(f"Grouping text boxes...")
        grouped_boxes = self._group_texts(text_boxes)

        self._debug_draw_text_boxes(in_image, grouped_boxes, "_grouped_textboxes")

        logger.info(f"Generating translation...")
        for box in grouped_boxes:
            box.text = self.translator.translate(box.text)

        logger.info(f"Generating text...")
        draw_text_boxes_on_image(out_image, grouped_boxes)

        logger.info(f"{out_image} Done!")

    def _debug_draw_text_boxes(self, image: Path, text_boxes, postfix=""):
        if logger.level >= 10: # fuck python logging
          im = Image.open(image)
          draw = ImageDraw.Draw(im)
          for box in text_boxes:
              draw.rectangle([box.x, box.y, box.x + box.w, box.y + box.h], outline="white")
          im.save(f"debug/{image.stem}{postfix}{image.suffix}")

    def _group_texts(self, text_boxes, tolerance=5):
        """
        Groups text boxes into clusters based on their vertical alignment and height similarity.
        This method takes a list of text boxes, sorts them by their vertical position (y-coordinate),
        and groups them into clusters. Text boxes are grouped together if they overlap vertically
        and have similar heights, with an additional tolerance for height differences caused by
        differences in text casing (e.g., uppercase vs lowercase).
        Args:
          text_boxes (list of TextBox): A list of TextBox objects to be grouped.
          tolerance (number): The tolerance value for height similarity.
        Returns:
          (list of TextBox): A list of grouped TextBox objects, where each group is represented
          as a single TextBox object created from the grouped boxes.
        """
        sorted_text_boxes = sorted(text_boxes, key=lambda box: box.y)
        grouped_boxes = []
        current_group = [sorted_text_boxes[0]]

        for box in sorted_text_boxes[1:]:
            last_box = current_group[-1]

            is_overlapping = box.y < last_box.y + last_box.h

            # Different casing results in different heights
            is_different_case = any(c.isupper() for c in last_box.text) != any(c.isupper() for c in box.text)
            is_similar_height = (abs(box.h - last_box.h)) < tolerance + is_different_case * tolerance

            if is_overlapping and is_similar_height:
                current_group.append(box)
            else:
                grouped_boxes.append(TextBox.from_grouped_boxes(current_group))
                current_group = [box]

        grouped_boxes.append(TextBox.from_grouped_boxes(current_group))
        return grouped_boxes
