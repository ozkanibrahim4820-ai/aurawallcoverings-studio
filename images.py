"""Read image container metadata without modifying or upscaling source pixels.

No full pixel decode: these checks are not a sharpness or print-readiness verdict.
"""
import struct
import zlib
from domain import ValidationError

MAX_FILE_BYTES = 20 * 1024 * 1024


def image_metadata(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FILE_BYTES:
        raise ValidationError("Dosya 1 bayt–20 MB aralığında olmalı.")
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        offset, width, height, have_data = 8, None, None, False
        chunks = 0
        while offset + 12 <= len(raw):
            chunks += 1
            if chunks > 10000:
                raise ValidationError("PNG parça sınırı aşıldı.")
            size = struct.unpack_from(">I", raw, offset)[0]
            kind = raw[offset+4:offset+8]
            end = offset + 12 + size
            if end > len(raw):
                raise ValidationError("PNG dosyası eksik veya bozuk.")
            data = raw[offset+8:offset+8+size]
            crc = struct.unpack_from(">I", raw, offset+8+size)[0]
            if zlib.crc32(kind + data) & 0xFFFFFFFF != crc:
                raise ValidationError("PNG bütünlük kontrolü başarısız.")
            if chunks == 1 and kind != b"IHDR":
                raise ValidationError("PNG başlığı bulunamadı.")
            if kind == b"IHDR":
                if size != 13 or width is not None:
                    raise ValidationError("PNG başlığı geçersiz.")
                width, height = struct.unpack_from(">II", data)
            if kind == b"IDAT":
                have_data = True
            if kind == b"IEND":
                if size or end != len(raw) or not have_data:
                    raise ValidationError("PNG sonlandırıcısı geçersiz.")
                return dimensions(width, height, "PNG", "image/png")
            offset = end
        raise ValidationError("PNG sonlandırıcısı bulunamadı.")
    if raw.startswith(b"\xff\xd8"):
        if not raw.endswith(b"\xff\xd9"):
            raise ValidationError("JPEG dosyası eksik veya bozuk.")
        pos = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while pos < len(raw) - 1:
            if raw[pos] != 0xFF:
                raise ValidationError("JPEG işaretçisi geçersiz.")
            while pos < len(raw) and raw[pos] == 0xFF:
                pos += 1
            if pos >= len(raw):
                break
            marker = raw[pos]
            pos += 1
            if marker in (0xDA, 0xD9):
                break
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(raw):
                break
            length = struct.unpack_from(">H", raw, pos)[0]
            if length < 2 or pos + length > len(raw):
                raise ValidationError("JPEG parçası eksik.")
            if marker in sof:
                if length < 8:
                    raise ValidationError("JPEG boyut başlığı geçersiz.")
                height, width = struct.unpack_from(">HH", raw, pos+3)
                return dimensions(width, height, "JPEG", "image/jpeg")
            pos += length
        raise ValidationError("JPEG piksel boyutu bulunamadı.")
    raise ValidationError("Yalnızca gerçek PNG ve JPEG dosyaları destekleniyor; dosya uzantısı yeterli değildir.")


def dimensions(width, height, format_name, mime):
    if not width or not height or width > 100000 or height > 100000:
        raise ValidationError("Piksel boyutları geçersiz veya desteklenen sınırın dışında.")
    return {"width_px": width, "height_px": height, "format": format_name, "mime": mime,
            "measurement": "file_header", "pixels_decoded": False,
            "preview_allowed": width * height <= 40_000_000,
            "orientation_note": "Kodlanmış piksel ölçüsü; EXIF yönlendirmesi uygulanmadı."}
