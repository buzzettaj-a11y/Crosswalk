"""A fixed install secret for tests. Tests never touch the real secret store."""
TEST_SECRET = bytes(range(32))
OTHER_SECRET = bytes(range(32, 64))
