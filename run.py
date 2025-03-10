import argparse
from detextify.detextifier import Detextifier

parser = argparse.ArgumentParser(prog='InPaintTranslate', usage='%(prog)s [options]')
parser.add_argument('-d', '--detector', default="PaddleOCR")
parser.add_argument('-in', '--inpainter', default="Local Stable Diffusion")
args = parser.parse_args()

if args.detector == "Tesseract":
  from detextify.text_detector import TesseractTextDetector
  text_detector = TesseractTextDetector("/usr/bin/tesseract")
elif args.detector == "Azure":
  from detextify.text_detector import AzureTextDetector
  text_detector = AzureTextDetector(AZURE_ENDPOINT, AZURE_API_KEY)
elif args.detector == "PaddleOCR":
  from detextify.text_detector import PaddleTextDetector
  text_detector = PaddleTextDetector()
  
if args.inpainter == "Local Stable Diffusion":
  from detextify.inpainter import LocalSDInpainter
  inpainter = LocalSDInpainter()
elif args.inpainter == "Stable Diffusion via Replicate":
  from detextify.inpainter import ReplicateSDInpainter
  inpainter = ReplicateSDInpainter(REPLICATE_API_KEY)
elif args.inpainter == "Dall-e via OpenAI":
  from detextify.inpainter import DalleInpainter
  inpainter = DalleInpainter(OPENAI_API_KEY)

detextifier = Detextifier(text_detector, inpainter)

detextifier.detextify("octopus.png", "octopus_out.png")