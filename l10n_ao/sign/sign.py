from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
import base64
import os
import tempfile

# This is the old method


def sign_content(content_data):
    dirname = os.path.dirname(__file__)
    print (dirname)
    with open(os.path.join(dirname, 'ChavePrivada.pem'), 'r') as reader:
        rsa_private_key = RSA.importKey(reader.read(), "")
        signer = PKCS1_v1_5.new(rsa_private_key)
        digest = SHA.new()
        digest.update(content_data.encode('utf-8'))
        sign = signer.sign(digest)
        res = base64.b64encode(sign)
        res = str(res)
    return res[2:-1] + ';1'


# def sign_content(content_data):
#     # openssl dgst -sha1
# def sign_content(content_data):
#     # openssl dgst -sha1 -sign ChavePrivada.pem -out signedbinay.sha1 f2.txt
#     # openssl enc -base64 -in signedbinay.sha1 -out signedcontent.txt -A
#     # os.system('openssl dgst -sha1 -sign ChavePrivada.pem -out signedbinay.sha1 f2.txt')
#
#     file_content_to_sign = tempfile.NamedTemporaryFile(delete=False)
#     file_content_to_sign.write(content_data.encode())
#     file_content_to_sign.close()
#
#     file_signed_binay = tempfile.NamedTemporaryFil-sign ChavePrivada.pem -out signedbinay.sha1 f2.txt
#     # openssl enc -base64 -in signedbinay.sha1 -out signedcontent.txt -A
#     # os.system('openssl dgst -sha1 -sign ChavePrivada.pem -out signedbinay.sha1 f2.txt')
#
#     file_content_to_sign = tempfile.NamedTemporaryFile(delete=False)
#     file_content_to_sign.write(content_data.encode())
#     file_content_to_sign.close()
#
#     file_signed_binay = tempfile.NamedTemporaryFile(delete=False)
#     file_signed_binay.close()
#
#     file_signed_text = tempfile.NamedTemporaryFile(delete=False)
#     file_signed_text.close()
#
#     dir_name = os.path.dirname(__file__)
#     file_private_key = os.path.join(dir_name, 'ChavePrivada.pem')
#     # file_content_to_sign = os.path.join(dirname, 'f2.txt')
#     # file_signed_binay = os.path.join(dirname, 'signedbinay.sha1')
#     # file_signed_text = os.path.join(dir_name, 'signedcontent.txt')
#
#     cmd1 = 'openssl dgst -sha1 -sign %s -out %s %s' % (file_private_key, file_signed_binay.name, file_content_to_sign.name, )
#     os.system(cmd1)
#     cmd2 = 'openssl enc -base64 -in %s -out %s -A' % (file_signed_binay.name, file_signed_text.name)
#     os.system(cmd2)
#
#     f = open(file_signed_text.name, "r")
#     signed_content = f.read()
#     return signed_content

