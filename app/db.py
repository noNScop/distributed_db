import time
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy, RetryPolicy
from cassandra.query import ConsistencyLevel

CONTACT_POINTS = ['127.0.0.1', '127.0.0.2', '127.0.0.3']
KEYSPACE = 'library'

_session = None
_cluster = None

def get_session():
    global _session, _cluster

    if _session:
        return _session

    for attempt in range(1, 11):
        try:
            _cluster = Cluster(
                contact_points=CONTACT_POINTS,
                load_balancing_policy=RoundRobinPolicy(),
                default_retry_policy=RetryPolicy(),
                connect_timeout=10,
            )
            _session = _cluster.connect()
            _session.default_consistency_level = ConsistencyLevel.QUORUM
            print("[db] Connected")
            return _session

        except Exception as e:
            print(f"[db] Attempt {attempt}/10 failed: {e}")
            if attempt < 10:
                time.sleep(2)

    raise RuntimeError("Could not connect to Cassandra after 10 attempts.")

def shutdown():
    global _session, _cluster

    if _session:
        print("[db] Shutting down session...")
        _session.shutdown()
        _session = None

    if _cluster:
        print("[db] Shutting down cluster...")
        _cluster.shutdown()
        _cluster = None