#Downloaded from and Modified:  https://docs.snowflake.com/en/_downloads/aeb84cdfe91dcfbd889465403b875515/sql-api-generate-jwt.py 
# To run this on the command line, enter:
#   python3 sql-api-generate-jwt.py --account=<account_identifier> --user=<username> --private_key_file_path=<path_to_private_key_file>

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat
from cryptography.hazmat.backends import default_backend
from datetime import timedelta, timezone, datetime
import base64
import hashlib
import logging

# This class relies on the PyJWT module (https://pypi.org/project/PyJWT/).
import jwt

logger = logging.getLogger(__name__)

try:
    from typing import Text
except ImportError:
    logger.debug('# Python 3.5.0 and 3.5.1 have incompatible typing modules.', exc_info=True)
    from typing_extensions import Text

ISSUER = "iss"
EXPIRE_TIME = "exp"
ISSUE_TIME = "iat"
SUBJECT = "sub"

class JWTGenerator(object):
    """
    Creates and signs a JWT with the specified private key file, username, and account identifier. The JWTGenerator keeps the
    generated token and only regenerates the token if a specified period of time has passed.
    """
    LIFETIME = timedelta(minutes=59)  # The tokens will have a 59 minute lifetime
    RENEWAL_DELTA = timedelta(minutes=54)  # Tokens will be renewed after 54 minutes
    ALGORITHM = "RS256"  # Tokens will be generated using RSA with SHA256

    def __init__(self, account: Text, user: Text, private_key_text: Text):
        """
        __init__ creates an object that generates JWTs for the specified user, account identifier, and private key.
        :param account: Your Snowflake account identifier. See https://docs.snowflake.com/en/user-guide/admin-account-identifier.html. Note that if you are using the account locator, exclude any region information from the account locator.
        :param user: The Snowflake username.
        :param private_key_file_path: Path to the private key file used for signing the JWTs.
        :param lifetime: The number of minutes (as a timedelta) during which the key will be valid.
        :param renewal_delay: The number of minutes (as a timedelta) from now after which the JWT generator should renew the JWT.
        """

        pem_prefix = '-----BEGIN RSA PRIVATE KEY-----\n'
        pem_suffix = '\n-----END RSA PRIVATE KEY-----'
        key = '{}{}{}'.format(pem_prefix, private_key_text, pem_suffix)
        a = bytearray(key, "utf-8")
        m = memoryview(a)

        self.account = self.prepare_account_name_for_jwt(account)
        self.user = user.upper()
        self.qualified_username = self.account + "." + self.user

        self.lifetime = JWTGenerator.LIFETIME
        self.renewal_delay = JWTGenerator.RENEWAL_DELTA
        self.private_key= load_pem_private_key(m, password=None,backend=default_backend())
        self.renew_time = datetime.now(timezone.utc)
        self.token = None

    def prepare_account_name_for_jwt(self, raw_account: Text) -> Text:
        """
        Prepare the account identifier for use in the JWT.
        For the JWT, the account identifier must not include the subdomain or any region or cloud provider information.
        :param raw_account: The specified account identifier. 
        :return: The account identifier in a form that can be used to generate JWT.
        """
        account = raw_account
        if not '.global' in account:
            # Handle the general case.
            idx = account.find('.')
            if idx > 0:
                account = account[0:idx]
        else:
            # Handle the replication case.
            idx = account.find('-')
            if idx > 0:
                account = account[0:idx]
        # Use uppercase for the account identifier.
        return account.upper()

    def get_token(self) -> Text:
        """
        Generates a new JWT. If a JWT has been already been generated earlier, return the previously generated token unless the
        specified renewal time has passed.
        :return: the new token
        """
        now = datetime.now(timezone.utc)  # Fetch the current time

        # If the token has expired or doesn't exist, regenerate the token.
        if self.token is None or self.renew_time <= now:
            logger.info("Generating a new token because the present time (%s) is later than the renewal time (%s)",
                        now, self.renew_time)
            # Calculate the next time we need to renew the token.
            self.renew_time = now + self.renewal_delay

            # Prepare the fields for the payload.
            # Generate the public key fingerprint for the issuer in the payload.
            public_key_fp = self.calculate_public_key_fingerprint(self.private_key)

            # Create our payload
            payload = {
                # Set the issuer to the fully qualified username concatenated with the public key fingerprint.
                ISSUER: self.qualified_username + '.' + public_key_fp,

                # Set the subject to the fully qualified username.
                SUBJECT: self.qualified_username,

                # Set the issue time to now.
                ISSUE_TIME: now,

                # Set the expiration time, based on the lifetime specified for this object.
                EXPIRE_TIME: now + self.lifetime
            }

            # Regenerate the actual token
            token = jwt.encode(payload, key=self.private_key, algorithm=JWTGenerator.ALGORITHM)
            # If you are using a version of PyJWT prior to 2.0, jwt.encode returns a byte string, rather than a string.
            # If the token is a byte string, convert it to a string.
            if isinstance(token, bytes):
              token = token.decode('utf-8')
            self.token = token
            logger.info("Generated a JWT with the following payload: %s", jwt.decode(self.token, key=self.private_key.public_key(), algorithms=[JWTGenerator.ALGORITHM]))

        return self.token

    def calculate_public_key_fingerprint(self, private_key: RSAPrivateKey) -> Text:
        """
        Given a private key in PEM format, return the public key fingerprint.
        :param private_key: private key string
        :return: public key fingerprint
        """
        # Get the raw bytes of public key.
        public_key_raw = private_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

        # Get the sha256 hash of the raw bytes.
        sha256hash = hashlib.sha256()
        sha256hash.update(public_key_raw)

        # Base64-encode the value and prepend the prefix 'SHA256:'.
        public_key_fp = 'SHA256:' + base64.b64encode(sha256hash.digest()).decode('utf-8')
        logger.info("Public key fingerprint is %s", public_key_fp)

        return public_key_fp
    
#added to expand usage and not just command line
def getJWTToken(account,user,private_key):
    return JWTGenerator(account, user, private_key).get_token()
