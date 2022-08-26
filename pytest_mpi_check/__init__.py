__version__ = "0.1"

def assert_mpi(comm, rank, cond, *args):
  if comm.rank == rank:
    if isinstance(cond, bool):
      assert cond
    else:
      assert cond(*args)
  else:
    pass
