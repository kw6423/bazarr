from subzero.language import Language

from subliminal_patch.core import ProviderPool, save_subtitles, search_external_subtitles
from subliminal_patch.subtitle import Subtitle


def _make_subtitle(language, content):
    subtitle = Subtitle(language)
    subtitle.content = content.encode("utf-8")
    return subtitle


def test_save_subtitles_keeps_multiple_files_per_language(tmp_path):
    video_path = tmp_path / "movie.mkv"

    first = _make_subtitle(Language.fromietf("en"), "1\n00:00:00,000 --> 00:00:01,000\nfirst\n")
    second = _make_subtitle(Language.fromietf("en"), "1\n00:00:00,000 --> 00:00:01,000\nsecond\n")

    saved = save_subtitles(str(video_path), [first, second], directory=str(tmp_path))

    assert len(saved) == 2
    assert saved[0].storage_path.endswith("movie.en.srt")
    assert saved[1].storage_path.endswith("movie.en.2.srt")
    assert (tmp_path / "movie.en.srt").exists()
    assert (tmp_path / "movie.en.2.srt").exists()


def test_search_external_subtitles_detects_numbered_forced_files(tmp_path):
    video_path = tmp_path / "movie.mkv"
    video_path.write_bytes(b"")

    first = _make_subtitle(Language.rebuild(Language.fromietf("en"), forced=True),
                           "1\n00:00:00,000 --> 00:00:01,000\nfirst\n")
    second = _make_subtitle(Language.rebuild(Language.fromietf("en"), forced=True),
                            "1\n00:00:00,000 --> 00:00:01,000\nsecond\n")

    save_subtitles(str(video_path), [first, second], directory=str(tmp_path))
    subtitles = search_external_subtitles(str(video_path))

    assert "movie.en.forced.srt" in subtitles
    assert "movie.en.2.forced.srt" in subtitles
    assert subtitles["movie.en.forced.srt"].basename == "en"
    assert subtitles["movie.en.forced.srt"].forced is True
    assert subtitles["movie.en.2.forced.srt"].basename == "en"
    assert subtitles["movie.en.2.forced.srt"].forced is True


class _FakeComputeScore:
    _scores = {"movie": {"hash": 119, "hearing_impaired": 1}}

    def __call__(self, matches, subtitle, video, use_hearing_impaired):
        return subtitle.fake_score, subtitle.fake_score


class _FakeSubtitle:
    hash_verifiable = False
    hearing_impaired_verifiable = False
    use_original_format = False
    release_info = "release"

    def __init__(self, language, score):
        self.language = language
        self.fake_score = score
        self.hearing_impaired = getattr(language, "hi", False)

    def get_matches(self, video):
        return {"title"}


def test_provider_pool_downloads_multiple_ranked_subtitles_per_language():
    pool = ProviderPool.__new__(ProviderPool)
    pool.download_subtitle = lambda subtitle: True

    language = Language.fromietf("en")
    subtitles = [
        _FakeSubtitle(language, 300),
        _FakeSubtitle(language, 250),
        _FakeSubtitle(language, 200),
    ]

    downloaded = pool.download_best_subtitles(
        subtitles=subtitles,
        video=object(),
        languages={language},
        min_score=0,
        hearing_impaired=False,
        only_one=False,
        compute_score=_FakeComputeScore(),
        max_subtitles_per_language=2,
    )

    assert len(downloaded) == 2
    assert [subtitle.fake_score for subtitle in downloaded] == [300, 250]
