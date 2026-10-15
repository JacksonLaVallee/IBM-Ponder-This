import array
import ctypes as C
import csv
import io
import json
import pathlib
import tempfile
import tokenize
import unittest

from certificate_math import factor, norm, witness_from_factors
from geometry import geometry, PS
from native import dll, U, I, inverse_bytes
from verify import verify

ROOT = pathlib.Path(__file__).resolve().parent

class Checks(unittest.TestCase):
    def test_witnesses(self):
        self.assertEqual(verify()['length'], 57)
        result=json.loads((ROOT/'solution.json').read_text())
        for k in range(57):
            n=result['a']+k*result['d']
            fs=factor(n)
            self.assertTrue(all(p%3!=2 or e%2==0 for p,e in fs))
            self.assertEqual(norm(witness_from_factors(fs)),n)
        for n in (result['a']-result['d'],result['a']+57*result['d']):
            self.assertTrue(any(p%3==2 and e%2 for p,e in factor(n)))

    def test_corruption_rejected(self):
        with (ROOT/'certificate.csv').open(newline='') as file:
            rows=list(csv.DictReader(file))
        rows[0]['x']=str(int(rows[0]['x'])+1)
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/'bad.csv'
            with path.open('w',newline='') as file:
                writer=csv.DictWriter(file,fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(ValueError):
                verify(path)

    def test_native_checker(self):
        pairs=json.loads((ROOT/'replay_expected.json').read_text())
        inputs=array.array('Q',[v for pair in pairs for v in pair])
        starts=array.array('Q',[0])*len(pairs)
        lengths=array.array('I',[0])*len(pairs)
        forwards=array.array('I',[0])*len(pairs)
        self.assertEqual(dll.check_pairs((U*len(inputs)).from_buffer(inputs),len(pairs),(U*len(pairs)).from_buffer(starts),(I*len(pairs)).from_buffer(lengths),(I*len(pairs)).from_buffer(forwards)),0)
        def good(n):
            return n==0 or all(p%3!=2 or e%2==0 for p,e in factor(n))
        for j,(a,d) in enumerate(pairs):
            k=0
            while k<60 and good(a+k*d):
                k+=1
            self.assertEqual(forwards[j],k)
            if k:
                while a>d and good(a-d):
                    a-=d
                    k+=1
            self.assertEqual((starts[j],lengths[j]),(a,k))

    def test_inverses(self):
        steps=[1,6,22547494573230,39345378030286350]
        primes=[59,71,83,89,101,997,99991]
        values=array.array('I')
        values.frombytes(inverse_bytes(steps,primes))
        self.assertEqual(list(values),[pow(d,-1,p) if d%p else 0 for d in steps for p in primes])

    def test_geometry(self):
        g,m,total,rad,offset,contribution=geometry(13,63)
        self.assertEqual(g,22547494573230)
        for root in (0,1,total//2,1718964480,1850910207,total-1):
            residue=0
            digits=[]
            remaining=root
            for count,off in zip(rad,offset):
                digit=remaining%count
                remaining//=count
                digits.append(digit)
                residue+=contribution[off+digit]
            residue%=m
            for j,p in enumerate(PS[6:13]):
                expected=[7,14][digits[j]] if j==0 else 7+digits[j]
                self.assertEqual(residue%p,expected)

    def test_no_comments(self):
        for path in ROOT.glob('*.py'):
            tokens=tokenize.generate_tokens(io.StringIO(path.read_text()).readline)
            self.assertFalse(any(token.type==tokenize.COMMENT for token in tokens),path.name)

if __name__=='__main__':
    unittest.main()
