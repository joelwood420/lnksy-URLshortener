import bcrypt
from db import execute_query


def create_user(email, password_hash):
    execute_query(
        "INSERT INTO USERS (email, password_hash) VALUES (?, ?)",
        (email, password_hash),
        commit=True
    )


def get_user_by_email(email):
    return execute_query(
        "SELECT * FROM USERS WHERE email = ?",
        (email,),
        fetchone=True
    )


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)


def login_user(email, password):
    user = get_user_by_email(email)
    if user and check_password(password, user[2]):
        return user
    return None







