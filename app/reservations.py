import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from schema import session, init_schema, prepare_queries
import threading

init_schema()
Q = prepare_queries()

def return_book(reservation_id):
    row = session.execute(Q["SELECT_RESERVATION"], (reservation_id,)).one()

    if not row:
        print(f"[!] Reservation {reservation_id} not found.")
        return

    book_row = session.execute(Q["SELECT_BOOK_COPIES"], (row.book_id,)).one()
    if book_row:
        session.execute(Q["UPDATE_BOOK_COPIES"], (book_row.available_copies + 1, row.book_id))

    session.execute(Q["UPDATE_RESERVATION_STATUS"], ('RETURNED', reservation_id))
    session.execute(Q["UPDATE_RESERVATION_BY_MEMBER_STATUS"], ('RETURNED', row.member_name, row.reserved_on, reservation_id))

    print(f"[~] '{row.book_title}' returned successfully.")


_active_count = 0
_active_lock = threading.Lock()
_all_done = threading.Condition(_active_lock)
_drain_in_progress = False
_drain_done = threading.Condition(_active_lock)

def _enter_region():
    with _drain_done:
        _drain_done.wait_for(lambda: not _drain_in_progress)
        global _active_count
        _active_count += 1

def _exit_region():
    with _active_lock:
        global _active_count
        _active_count -= 1
        if _active_count == 0:
            _all_done.notify_all()

def _start_drain():
    with _active_lock:
        global _drain_in_progress
        _drain_in_progress = True

def _finish_drain():
    with _active_lock:
        global _drain_in_progress
        _drain_in_progress = False
        _drain_done.notify_all()

def _wait_for_drain():
    with _all_done:
        _all_done.wait_for(lambda: _active_count == 0)


def make_reservation(book_id, member_name):
    _enter_region()
    exited = False

    try:
        for _ in range(100):
            row = session.execute(Q["SELECT_BOOK"], (book_id,)).one()

            if not row:
                print("[!] Book not found.")
                return None

            if row.available_copies <= 0:
                print(f"[!] '{row.title}' is currently unavailable.")
                return None

            try:
                applied = session.execute(Q["UPDATE_BOOK_COPIES_CAS"], (row.available_copies - 1, book_id, row.available_copies)).one()
            except Exception as e:
                print(f"[!] Reservation failed - {e}. Retrying.")
                _exit_region()
                exited = True
                _start_drain()
                _wait_for_drain()

                try:
                    row = session.execute(Q["SELECT_BOOK"], (book_id,)).one()
                    fresh = session.execute(Q["SELECT_BOOK_COPIES_FULL"], (book_id,)).one()
                    active = session.execute(Q["COUNT_ACTIVE_RESERVATIONS"], (book_id,)).one().count
                    true_available = fresh.total_copies - active

                    print(f"[~] Restoring {true_available-row.available_copies} lost copies for '{fresh.title}', retrying...")
                    session.execute(Q["UPDATE_BOOK_COPIES_CAS"], (true_available, book_id, row.available_copies))
                finally:
                    _finish_drain()

                exited = False
                _enter_region()
                continue

            if applied.applied:
                break
        else:
            print("[!] Reservation failed - system is under heavy load. Please try again.")
            return None

        res_id = uuid.uuid4()
        now = datetime.now(ZoneInfo("Europe/Warsaw"))
        due = now + timedelta(days=14)

        try:
            session.execute(Q["INSERT_RESERVATION"], (res_id, book_id, row.title, member_name, now, due))
            session.execute(Q["INSERT_RESERVATION_BY_MEMBER"], (member_name, row.title, now, res_id, due))
        except Exception as e:
            print(f"[!] Reservation write failed: {e}")
            raise e

        print(f"[+] Reservation created: {res_id} — '{row.title}' due {due.strftime('%Y-%m-%d')}")
        return res_id

    finally:
        if not exited:
            _exit_region()


def get_reservation(reservation_id):
    row = session.execute(Q["SELECT_RESERVATION_FULL"], (reservation_id,)).one()

    if row:
        print(f"\n--- Reservation ---")
        print(f"  ID:      {row.reservation_id}")
        print(f"  Book:    {row.book_title}")
        print(f"  Member:  {row.member_name}")
        print(f"  Date:    {row.reserved_on.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Due:     {row.due_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Status:  {row.status}")
    else:
        print(f"[!] Reservation {reservation_id} not found.")
    return row


def get_reservations_by_member(member_name):
    rows = list(session.execute(Q["SELECT_RESERVATIONS_BY_MEMBER"], (member_name,)))

    if not rows:
        print(f"[!] No reservations found for member {member_name}.")
        return []

    print(f"\n--- Reservations for member {member_name} ({len(rows)} found) ---")
    for r in rows:
        print(
            f"  [{r.status}] {r.book_title} — "
            f"reserved {r.reserved_on.strftime('%Y-%m-%d %H:%M:%S')} · "
            f"due {r.due_date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    return rows