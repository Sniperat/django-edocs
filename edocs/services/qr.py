import os
from pathlib import Path
from django.conf import settings
import qrcode
from PIL import Image, ImageDraw, ImageFont


class QRCodeService:
    """
    Generates QR code images with 4-digit security code and E-IMZO stamp images.
    """

    @classmethod
    def get_output_dir(cls) -> Path:
        media_root = getattr(settings, "MEDIA_ROOT", "/tmp")
        qr_dir = Path(media_root) / "edocs" / "qrcodes"
        qr_dir.mkdir(parents=True, exist_ok=True)
        return qr_dir

    @classmethod
    def generate_document_qr(cls, guid: str, view_url: str, security_code: str = "") -> str:
        """
        Generates QR image with an optional vertical 4-digit security code along the left edge.
        Returns the absolute filesystem path of the saved PNG.
        """
        qr_dir = cls.get_output_dir()
        output_path = qr_dir / f"{guid}.png"

        # 1. Base QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=1,
        )
        qr.add_data(view_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        qr_w, qr_h = qr_img.size

        # 2. Optional 4-digit security code rotated 90 degrees counter-clockwise
        code_str = str(security_code or "").strip()
        if code_str:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if not os.path.exists(font_path):
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

            font_size = int(qr_h * 0.22)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = ImageFont.load_default()

            bbox = font.getbbox(code_str)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            padding = 4
            txt_img = Image.new("RGBA", (text_w + padding * 2, text_h + padding * 2), (255, 255, 255, 0))
            d = ImageDraw.Draw(txt_img)
            d.text((padding - bbox[0], padding - bbox[1]), code_str, font=font, fill=(35, 35, 35, 255))

            rotated_txt = txt_img.rotate(90, expand=True)
            rot_w, rot_h = rotated_txt.size

            gap = int(qr_w * 0.08)
            total_w = rot_w + gap + qr_w
            total_h = max(qr_h, rot_h)

            final_img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
            txt_y = (total_h - rot_h) // 2
            final_img.paste(rotated_txt, (0, txt_y), rotated_txt)

            qr_y = (total_h - qr_h) // 2
            final_img.paste(qr_img, (rot_w + gap, qr_y))
        else:
            final_img = qr_img.convert("RGB")

        final_img.save(str(output_path), "PNG")
        return str(output_path)
