from pytest_parallel.utils import

class callspec_mock:
  def __init__(self, n_procs):
    self.n_procs = n_procs
  def getparam(self, s):
    assert s == 'comm'
    return self.n_procs

class item_mock:
  def __init__(self, name, n_procs):
    self.name = name
    self.callspec = callspec_mock(n_procs)

def test_group_items_by_parallel_steps():
  n_workers = 4
  items = [item_mock('a',2),item_mock('b',3),item_mock('c',1),item_mock('d',100),item_mock('e',1),item_mock('f',1)]

  items_by_steps,items_to_skip = group_items_by_parallel_steps(items, n_workers)
  assert len(items_by_steps) == 2
  assert len(items_by_steps[0]) == 3
  assert len(items_by_steps[1]) == 2
  assert items_by_steps[0][0].name = 'a'
  assert items_by_steps[0][1].name = 'c'
  assert items_by_steps[0][2].name = 'e'
  assert items_by_steps[1][0].name = 'b'
  assert items_by_steps[1][1].name = 'f'

  assert len(items_to_skip) == 1
  assert items_to_skip[0].name == 'd'
