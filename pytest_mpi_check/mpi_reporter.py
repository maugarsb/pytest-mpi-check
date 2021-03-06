import pytest

from mpi4py import MPI
from collections import defaultdict

from _pytest.reports import TestReport
from _pytest._code.code import ExceptionChainRepr, ReprTraceback, ReprEntry, ReprEntryNative, ReprFileLocation

class MPIReporter(object):
  __slots__ = ["mpi_reports", "comm", "n_send", "post_done", "reports_gather"]
  def __init__(self, comm):
    self.comm           = comm
    self.n_send         = 0
    self.mpi_reports    = defaultdict(list)
    self.post_done      = False
    self.reports_gather = defaultdict(list)


  @pytest.hookimpl(tryfirst=True, hookwrapper=True)
  def pytest_runtest_makereport(self, item):
    # print("pytest_runtest_makereport", item._sub_comm)
    outcome = yield
    report = outcome.get_result()
    if(item._sub_comm != MPI.COMM_NULL):
      report._i_rank = item._sub_comm.Get_rank()
      report._n_rank = item._sub_comm.Get_size()
    else:
      report._i_rank = 0
      report._n_rank = 1

    # report._i_rank = MPI.COMM_WORLD.Get_rank()
    # report._n_rank = MPI.COMM_WORLD.Get_size()

  @pytest.mark.tryfirst
  def pytest_runtest_logreport(self, report):
    """
    """
    # print("MPIReporter::pytest_runtest_logreport", report.when)

    # if(self.comm.Get_rank() != 0):
    # Egalemnt possible d'envoyer que si il est execute (donc MPI_COMM != NULL )
    # Si skip uniquement le rang 0 le fait

    has_runned  = not report.skipped and report.when == "call"
    mpi_skipped = report.skipped and self.comm.Get_rank() == 0 and report.when == 'setup'
    if(has_runned or mpi_skipped):
      # > Attention report peut être gros (stdout dedans etc ...)
      self.comm.send(report, dest=0, tag=self.n_send)
      self.n_send += 1

  def gather_report(self):
    """
    """
    assert(self.post_done == True)


    # -----------------------------------------------------------------
    for nodeid, report_list in self.mpi_reports.items():
      # print("nodeid::", nodeid)

      assert(len(report_list) > 0)

      # > Initialize with the first reporter
      i_rank_report_init, report_init = report_list[0]

      greport = TestReport(nodeid,
                           report_init.location,
                           report_init.keywords,
                           report_init.outcome,
                           report_init.longrepr, # longrepr
                           report_init.when)

      # print("report_init.location::", report_init.location)
      # print("report_init.longrepr::", type(report_init.longrepr), report_init.longrepr)

      collect_longrepr = []
      # > We need to rebuild a TestReport object, location can be false
      # > Report appears in rank increasing order
      if greport.outcome != 'skipped':
        # Skipped test are only know by proc 0 -> no merge required
        for i_rank_report, test_report in report_list:

          if(test_report.outcome == 'failed'):
            greport.outcome = test_report.outcome

          if(test_report.longrepr):
            fake_trace_back = ReprTraceback([ReprEntryNative(f"\n\n----------------------- On rank [{test_report._i_rank}/{test_report._n_rank}] / Global [{i_rank_report}/{self.comm.Get_size()}] ----------------------- \n\n")], None, None)
            collect_longrepr.append((fake_trace_back     , ReprFileLocation(*report_init.location), None))
            collect_longrepr.append((test_report.longrepr, ReprFileLocation(*report_init.location), None))

        if(len(collect_longrepr) > 0):
          greport.longrepr = ExceptionChainRepr(collect_longrepr)

      self.reports_gather[nodeid] = [greport]
    # -----------------------------------------------------------------

  @pytest.mark.tryfirst
  def pytest_sessionfinish(self, session):
    """
    """
    nb_recv_tot = self.comm.reduce(self.n_send, root=0)
    # print("nb_recv_tot::", nb_recv_tot)
    # print("\n MPIReporter::pytest_sessionfinish:: ", len(self.mpi_reports.items()))

    self.comm.Barrier()

    if self.comm.Get_rank() == 0:
      for i_msg in range(nb_recv_tot):
        status = MPI.Status()
        # print(dir(status))
        is_ok_to_recv = self.comm.probe(MPI.ANY_SOURCE, MPI.ANY_TAG, status=status)
        if is_ok_to_recv:
          report = self.comm.recv(source=status.Get_source(), tag=status.Get_tag())
          # > On fait un dictionnaire en attendant de faire list + tri indirect
          if report:
            # self.mpi_reports[(status.Get_source(),report.nodeid)].append(report)
            self.mpi_reports[report.nodeid].append((status.Get_source(), report))

      # > Sort by incrizing rank number
      for node_id, report_list in self.mpi_reports.items():
        report_list.sort(key = lambda tup: tup[0])

    self.comm.Barrier()

    self.post_done = True

    self.gather_report()
