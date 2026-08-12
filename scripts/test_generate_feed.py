import runpy
import xml.etree.ElementTree as ET
from pathlib import Path


def test_generated_feed_is_valid_atom():
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'generate_feed.py'))
    feed_path = Path(__file__).resolve().parents[1] / 'docs' / 'feed.xml'
    root = ET.fromstring(feed_path.read_text(encoding='utf-8'))
    assert root.tag == '{http://www.w3.org/2005/Atom}feed'
    entries = root.findall('{http://www.w3.org/2005/Atom}entry')
    assert entries
    alternate = root.find("{http://www.w3.org/2005/Atom}link[@rel='alternate']")
    assert alternate is not None
    assert alternate.get('href') == 'https://bxs1024.github.io/weekly-report/'
    for entry in entries:
        link = entry.find('{http://www.w3.org/2005/Atom}link')
        assert link is not None
        assert link.get('href')
        assert entry.find('{http://www.w3.org/2005/Atom}published') is not None


if __name__ == '__main__':
    test_generated_feed_is_valid_atom()
    print('generate feed tests passed')
