# ====================================================================
# This file is part of LockByte.
# LockByte is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3 of the License.
# LockByte is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with LockByte. If not, see <https://www.gnu.org/licenses/>.
# ====================================================================

from argon2 import PasswordHasher
from argon2.low_level import Type
from Crypto.Protocol.KDF import scrypt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from os import urandom, path as ospath


class LockByteUser:
    '''
    Class to implement password based 256-bit AES encryption / decryption using argon2 hashing algorithm and scrypt KDF
    '''
    hashing_params = {"type": Type.ID,
                      "salt_len": 32,
                      "hash_len": 32,
                      "time_cost": 3,
                      "parallelism": 4}

    key_params = {"key_len": 32, 
                  "N": 2**(20),
                  "r": 8,
                  "p": 1}

    def __init__(self, passphrase: str, **kwargs) -> None:
        '''
        Constructor for LockByte class

        :param passphrase: user password to be used for encryption
        '''
        self.salt = urandom(32) # create a random salt
        self.hashing_obj = PasswordHasher(**self.hashing_params) # create hashing object
        self.pass_hash = self.hashing_obj.hash(passphrase, salt=self.salt) # generate password hash
        self._key = passphrase
        self.cipher = None

    def validate_and_generate(self, mode: int, extracted_hash = None, iv:bytes = None) -> bool:
        '''
        Function to validate user password and generate cipher object

        :param mode: encryption/decryption
        :param extracted-hash: hash to be compared in case of decryption
        :param iv: initialization vector to be used 
        '''
        if mode == 0:  # mode = 0 (decryption), validate user password
            if not self.hashing_obj.verify(extracted_hash, self._key):
                return False
            else: # verification successful 
                self.salt = extracted_hash.split('$')[-2]
                if self.hashing_obj.check_needs_rehash(extracted_hash):
                    self.pass_hash = self.hashing_obj.hash(
                        password=self._key, salt=self.salt)
                else:
                    self.pass_hash = extracted_hash
        else: # mode = 1 (encryption)
            self.salt = self.pass_hash.split('$')[-2]

        self._key = scrypt(password=self._key,
                           salt=self.salt, **self.key_params)
        if iv is not None: # set initialization vector if decryption
            self.cipher = AES.new(self._key, AES.MODE_CBC, iv=iv) # create cipher object
        else:
            self.cipher = AES.new(self._key, AES.MODE_CBC) # create cipher object

        return True

    # fubction to generate unique file names
    def get_unique_name(self, f:str):
        fnew = f
        root, ext = ospath.splitext(f)
        i = 0
        while ospath.exists(fnew):
            i += 1
            fnew = '%s(%i)%s' % (root, i, ext)
        return fnew

    # encryption function
    def encrypt(self, file, file_path: str) -> None:
        '''
        Function to handle encryption process

        :param file: open file object of the file to be encrypted
        :param file_path: path to file to be encrypted
        '''
        try:
            file_content = file.read()
            en_file = self.cipher.encrypt(pad(file_content, AES.block_size, 'pkcs7'))
            iv = self.cipher.iv
            file_name_new = file_path + ".lockbyte"
            file_name_new = self.get_unique_name(file_name_new)
            with open(file_name_new, "wb") as ef:
                ef.write(iv)
                ef.write(self.pass_hash.encode("ascii"))
                ef.write(en_file)
        except:
            raise

    # decryption function
    def decrypt(self, file, file_path: str) -> str:
        '''
        Function to handle decrytion process

        :param file: open file object of the file to be decrypted
        :param file_path: path to file to be decrypted

        Returns decrypted file path
        '''
        try:
            file_content = file.read()
            iv = file_content[:16]
            extracted_hash = file_content[16:134].decode("ascii")
            if self.validate_and_generate(0, extracted_hash, iv):
                de_file = unpad(self.cipher.decrypt(
                    file_content[134:]), AES.block_size, 'pkcs7')
                file_name_new = file_path.split('.')[-3]+"_decrypted"+'.'+file_path.split('.')[-2].split('(')[0]
                file_name_new = self.get_unique_name(file_name_new)
                with open(file_name_new, "wb") as df:
                    df.write(de_file)
            return file_name_new
        except:
            raise