# -*- coding: utf-8 -*-
import qrcode
import base64
from io import BytesIO


def generate_qr_code(values):
    qr = qrcode.QRCode(
             version=1,
             error_correction=qrcode.constants.ERROR_CORRECT_L,
             box_size=20,
             border=4,
             )
    qr.add_data(values)
    qr.make(fit=True)
    img = qr.make_image()
    temp = BytesIO()
    img.save(temp, kind="PNG")
    qr_img = base64.b64encode(temp.getvalue())
    return qr_img