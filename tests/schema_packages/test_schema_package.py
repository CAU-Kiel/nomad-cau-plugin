import os.path

from nomad.client import normalize_all, parse


def test_schema_package():
    test_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'test.archive.yaml',
    )
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.message == 'Hello Markus!'


def test_michaela_schema_package():
    test_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'test_michaela.archive.yaml',
    )
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.name == 'Michaela'
    assert entry_archive.data.external_id == 'michaela-001'
    assert entry_archive.data.xrd is not None
