from db import get_session

session = get_session()

def init_schema():
    session.execute("""
    CREATE KEYSPACE IF NOT EXISTS library
        WITH replication = {
        'class': 'SimpleStrategy',
        'replication_factor': 3
    };
    """)

    session.set_keyspace('library')

    session.execute("""
    CREATE TABLE IF NOT EXISTS books (
        book_id             UUID PRIMARY KEY,
        title               TEXT,
        author              TEXT,
        total_copies        INT,
        available_copies    INT
    );
    """)

    session.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id  UUID PRIMARY KEY,
        book_id         UUID,
        book_title      TEXT,
        member_name     TEXT,
        reserved_on     TIMESTAMP,
        due_date        TIMESTAMP,
        status          TEXT
    );
    """)

    session.execute("""
    CREATE TABLE IF NOT EXISTS reservations_by_member (
        member_name     TEXT,
        book_title      TEXT,
        reserved_on     TIMESTAMP,
        reservation_id  UUID,
        due_date        TIMESTAMP,
        status          TEXT,
        PRIMARY KEY (member_name, reserved_on, reservation_id)
    ) WITH CLUSTERING ORDER BY (reserved_on DESC);
    """)

    print("[schema] Keyspace and tables ready.")


def prepare_queries():
    return {
        # --- reservations.py ---
        "SELECT_RESERVATION": session.prepare("""
            SELECT book_id, book_title, member_name, reserved_on
            FROM reservations WHERE reservation_id = ?
        """),
        "SELECT_RESERVATION_FULL": session.prepare(
            "SELECT * FROM reservations WHERE reservation_id = ?"
        ),
        "UPDATE_RESERVATION_STATUS": session.prepare("""
            UPDATE reservations SET status = ?
            WHERE reservation_id = ?
        """),
        "INSERT_RESERVATION": session.prepare("""
            INSERT INTO reservations
            (reservation_id, book_id, book_title, member_name, reserved_on, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
        """),
        "SELECT_RESERVATIONS_BY_MEMBER": session.prepare("""
            SELECT reservation_id, book_title, reserved_on, due_date, status
            FROM reservations_by_member WHERE member_name = ?
        """),
        "UPDATE_RESERVATION_BY_MEMBER_STATUS": session.prepare("""
            UPDATE reservations_by_member SET status = ?
            WHERE member_name = ? AND reserved_on = ? AND reservation_id = ?
        """),
        "INSERT_RESERVATION_BY_MEMBER": session.prepare("""
            INSERT INTO reservations_by_member
            (member_name, book_title, reserved_on, reservation_id, due_date, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """),
        "SELECT_BOOK": session.prepare(
            "SELECT title, available_copies FROM books WHERE book_id = ?"
        ),
        "SELECT_BOOK_COPIES": session.prepare(
            "SELECT available_copies FROM books WHERE book_id = ?"
        ),
        "UPDATE_BOOK_COPIES": session.prepare(
            "UPDATE books SET available_copies = ? WHERE book_id = ?"
        ),
        "UPDATE_BOOK_COPIES_CAS": session.prepare("""
            UPDATE books SET available_copies = ?
            WHERE book_id = ?
            IF available_copies = ?
        """),

        # --- books.py ---
        "SELECT_ONE_BOOK_ID": session.prepare(
            "SELECT book_id FROM books LIMIT 1"
        ),
        "SELECT_ALL_BOOKS": session.prepare(
            "SELECT book_id, title, author, total_copies, available_copies FROM books"
        ),
        "SELECT_BOOK_COPIES_FULL": session.prepare(
            "SELECT title, total_copies, available_copies FROM books WHERE book_id = ?"
        ),
        "SELECT_ALL_RESERVATION_IDS": session.prepare(
            "SELECT reservation_id FROM reservations"
        ),
        "SELECT_ALL_MEMBERS": session.prepare(
            "SELECT DISTINCT member_name FROM reservations_by_member"
        ),
        "SELECT_RESERVATIONS_BY_MEMBER_IDS": session.prepare(
            "SELECT reservation_id FROM reservations_by_member WHERE member_name = ?"
        ),
        "INSERT_BOOK": session.prepare("""
            INSERT INTO books (book_id, title, author, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?)
        """),
        "UPDATE_BOOK_COPIES_FULL_CAS": session.prepare("""
            UPDATE books
            SET total_copies = ?, available_copies = ?
            WHERE book_id = ?
            IF available_copies = ?
        """),
        "DELETE_BOOK": session.prepare(
            "DELETE FROM books WHERE book_id = ?"
        ),
        "DELETE_RESERVATION": session.prepare(
            "DELETE FROM reservations WHERE reservation_id = ?"
        ),
        "DELETE_RESERVATIONS_BY_MEMBER": session.prepare(
            "DELETE FROM reservations_by_member WHERE member_name = ?"
        ),
        "COUNT_ACTIVE_RESERVATIONS": session.prepare("""
            SELECT COUNT(*) FROM reservations WHERE book_id = ? AND status = 'ACTIVE'
            ALLOW FILTERING
        """),
    }