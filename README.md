# JWTGenerator
#Downloaded from and Modified:  https://docs.snowflake.com/en/_downloads/aeb84cdfe91dcfbd889465403b875515/sql-api-generate-jwt.py 
# This class relies on the PyJWT module (https://pypi.org/project/PyJWT/).
#Creates and signs a JWT with the specified private key file, username, and account identifier. The JWTGenerator keeps the generated token and only regenerates the token if a specified period of time has passed.
# 
# To run this on the command line to connect to Snowflake, enter:
#   python3 sql-api-generate-jwt.py --account=<account_identifier> --user=<username> --private_key_file_path=<path_to_private_key_file>
