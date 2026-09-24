import pymysql
from django.db.backends.base.base import BaseDatabaseWrapper

pymysql.install_as_MySQLdb()
BaseDatabaseWrapper.check_database_version_supported = lambda self: None
