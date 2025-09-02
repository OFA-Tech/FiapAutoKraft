from enum import Enum


class DataBaseType(str, Enum):
    SQLSERVER = "SQLSERVER"
    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    MARIADB = "MARIADB"
    ORACLE = "ORACLE"
    FIREBIRD = "FIREBIRD"
