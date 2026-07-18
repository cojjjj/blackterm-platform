from blackterm_recon.database import ScanRepository
from blackterm_recon.case_reporting import write_case_report

def test_case_evidence_timeline_search_and_export(tmp_path):
    repo=ScanRepository(str(tmp_path/'db.sqlite'))
    cid=repo.create_case('Operation Violet','Authorized investigation')
    repo.add_case_note(cid,'Review exposed remote access')
    eid=repo.add_case_evidence(cid,'DNS','DNS snapshot','resolver','A 127.0.0.1')
    assert eid>0
    assert repo.case_evidence(cid)[0]['sha256']
    assert len(repo.case_timeline(cid))>=3
    assert repo.search_cases('remote')[0]['id']==cid
    out=write_case_report(repo,cid,tmp_path/'case.json','json')
    assert out.exists() and 'Operation Violet' in out.read_text()

def test_case_status(tmp_path):
    repo=ScanRepository(str(tmp_path/'db.sqlite')); cid=repo.create_case('Test')
    repo.update_case_status(cid,'ACTIVE')
    assert repo.list_cases()[0]['status']=='ACTIVE'
