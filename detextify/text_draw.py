from typing import Sequence
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from detextify.text_detector import TextBox 

def _get_wrapped_text(text: str, font: ImageFont.ImageFont, line_length: int):
  lines = ['']
  for word in text.split():
    line = f'{lines[-1]} {word}'.strip()
    if font.getlength(line) <= line_length:
      lines[-1] = line
    else:
      lines.append(word)
  return '\n'.join(lines)

def _get_text_size(box: TextBox) -> int:
  all_lowercase = box.text.lower() == box.text
  return ((box.h-20)/box.lines) + all_lowercase*8

def _draw_box(img: Image, box: TextBox) -> Image:
  # Write text to transparent image
  text_img = Image.new('RGBA', img.size)
  draw = ImageDraw.Draw(text_img)
  font = ImageFont.truetype("arial.ttf", _get_text_size(box))

  draw.text((box.x+10, box.y+10), _get_wrapped_text(box.text, font, box.w), (255, 255, 255), font=font, align="center")

  text_bb = text_img.getbbox()
  if text_bb[2]-text_bb[0] > box.w:
    # Need a clean image to keep position
    text_img2 = Image.new('RGBA', img.size)
    # Resize text image to fit `box`
    text_img2.paste(text_img.crop(text_bb).resize((int(box.w), int(box.h))))
    text_img = text_img2

  return Image.alpha_composite(img, text_img)

def draw_text_boxes_on_image(image_path: str, text_boxes: Sequence[TextBox]):
  img = Image.open(image_path).convert("RGBA") # alpha_composite needs RGBA
  
  for box in text_boxes:
    img = _draw_box(img, box)
  
  img.save(image_path)