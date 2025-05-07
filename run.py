from inpaint_translate.logger_config import get_logger
import logging
import os
import argparse
from pathlib import Path
from deep_translator import MyMemoryTranslator

parser = argparse.ArgumentParser(prog='InPaintTranslate', usage='%(prog)s [options]')
parser.add_argument('input', type=str, help="Input image path")
parser.add_argument('-d', '--detector', choices=["Tesseract", "Azure", "PaddleOCR"], default="PaddleOCR", help="Text detector to use")
parser.add_argument('-in', '--inpainter', choices=["Local Stable Diffusion", "Stable Diffusion via Replicate", "Dall-e via OpenAI"], default="Local Stable Diffusion", help="Inpainter to use")
#parser.add_argument('-t', '--translator', choices=["MyMemory"], default="MyMemory", help="Translator to use")
parser.add_argument('-l', '--language', type=str, default="hu-HU", help="ISO standard langugaename to translate to. Note that limitations apply to the free MyMemory API. See https://mymemory.translated.net/doc/usagelimits.php")
parser.add_argument('-o', '--output', type=str, default="out.png", help="Output image path")
parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose logging")
args = parser.parse_args()

logger = get_logger()
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

from inpaint_translate.inpaint_translate import InpaintTranslator

match args.detector:
  case "Tesseract":
    from inpaint_translate.text_detector import TesseractTextDetector
    text_detector = TesseractTextDetector("/usr/bin/tesseract")
  case "Azure":
    from inpaint_translate.text_detector import AzureTextDetector
    text_detector = AzureTextDetector(os.environ["AZURE_ENDPOINT"], os.environ["AZURE_API_KEY"])
  case "PaddleOCR":
    from inpaint_translate.text_detector import PaddleTextDetector
    text_detector = PaddleTextDetector()
  case _:
    raise ValueError(f"Unknown text detector: {args.detector}")
  
match args.inpainter:
  case "Local Stable Diffusion":
    from inpaint_translate.inpainter import LocalSDInpainter
    inpainter = LocalSDInpainter()
  case "Stable Diffusion via Replicate":
    from inpaint_translate.inpainter import ReplicateSDInpainter
    inpainter = ReplicateSDInpainter(os.environ["REPLICATE_API_KEY"])
  case "Dall-e via OpenAI":
    from inpaint_translate.inpainter import DalleInpainter
    inpainter = DalleInpainter(os.environ["OPENAI_API_KEY"])
  case _:
    raise ValueError(f"Unknown inpainter: {args.inpainter}")

inpaint_translator = InpaintTranslator(text_detector, inpainter, MyMemoryTranslator(source="en-US", target=args.language))

## Create the output directory if it doesn't exist
if args.verbose:
  debug_folder = Path("debug")
  debug_folder.mkdir(exist_ok=True)

inpaint_translator.inpaint_translate(Path(args.input), Path(args.output))
