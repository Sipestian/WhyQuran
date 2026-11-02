"""Exercise the read-only independent auditor against real and tampered copies."""
import hashlib,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'research/experiments/chromosome-controls'
SCRIPT=ART/'audit_independent.py'
class IndependentAuditTests(unittest.TestCase):
 def run_audit(self, directory=ART):
  return subprocess.run(['python3',str(SCRIPT),'--artifacts',str(directory)],capture_output=True,text=True,cwd=ROOT)
 def test_accepts_unchanged_data_without_writing_it(self):
  before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in ART.glob('*.json*')}
  result=self.run_audit()
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(json.loads(result.stdout)['checked_draws'],10000)
  self.assertEqual(before,{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in ART.glob('*.json*')})
 def tamper(self,change,message):
  with tempfile.TemporaryDirectory(prefix='whyqaraan-controls-audit-') as tmp:
   d=Path(tmp)
   for file in ART.iterdir():
    if file.is_file(): shutil.copy2(file,d/file.name)
   path=d/'draws.jsonl'; lines=path.read_text().splitlines(); change(lines)
   path.write_text('\n'.join(lines)+'\n')
   manifest=json.loads((d/'run-manifest.json').read_text())
   manifest['artifact_hashes']['draws.jsonl']=hashlib.sha256(path.read_bytes()).hexdigest()
   (d/'run-manifest.json').write_text(json.dumps(manifest))
   result=self.run_audit(d)
   self.assertEqual(result.returncode,1,result.stderr)
   self.assertIn(message,result.stderr)
 def test_rejects_rehashed_wrong_total(self):
  def change(lines):
   row=json.loads(lines[0]);row['totals_by_rule']['C3']['A']+=1;lines[0]=json.dumps(row)
  self.tamper(change,'totals at draw 1')
 def test_rejects_rehashed_missing_draw(self):
  self.tamper(lambda lines:lines.pop(),'expected 10000 draws')
 def test_rejects_rehashed_wrong_replay(self):
  def change(lines):
   row=json.loads(lines[0]);row['slot_refs'][0],row['slot_refs'][3]=row['slot_refs'][3],row['slot_refs'][0];lines[0]=json.dumps(row)
  self.tamper(change,'replay at draw 1')
if __name__=='__main__':unittest.main()
