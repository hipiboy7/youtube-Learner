"""domain/models 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 4절, 요구사항 FR-9~FR-15.

정상 케이스만 확인하면 아무것도 거부하지 않는 모델도 통과한다. 거부 케이스가 이 파일의 핵심이다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from youtube_learner.constants import PIPELINE_VERSION, AnalysisKind, TranscriptSource, TranscriptStatus, VideoKind
from youtube_learner.domain.models import (
    AnalysisResult,
    AnalyzerInfo,
    ChannelRef,
    TranscriptResult,
    TranscriptSegment,
    Video,
    VideoStub,
)

VID = "L81RWsnY-vY"
CH = "UCgheNMc3gGHLsT-RISdCzDQ"


def seg(idx: int, start: int, end: int, text: str = "말") -> TranscriptSegment:
    return TranscriptSegment(idx=idx, start_ms=start, end_ms=end, text=text)


class TestChannelRef:
    def test_accepts_channel_id(self):
        ref = ChannelRef(yt_channel_id=CH, handle=None, url=f"https://www.youtube.com/channel/{CH}")
        assert ref.yt_channel_id == CH

    def test_accepts_handle_only(self):
        ref = ChannelRef(yt_channel_id=None, handle="@sebasi15", url="https://www.youtube.com/@sebasi15")
        assert ref.handle == "@sebasi15"

    def test_rejects_when_neither_identifier(self):
        """FR-10 — 채널ID 도 핸들도 없으면 채널을 특정할 수 없다."""
        with pytest.raises(ValidationError):
            ChannelRef(yt_channel_id=None, handle=None, url="https://www.youtube.com/")

    @pytest.mark.parametrize("bad", ["sebasi15", "UC123", "@", ""])
    def test_rejects_bad_channel_id(self, bad):
        with pytest.raises(ValidationError):
            ChannelRef(yt_channel_id=bad, handle=None, url="x")

    def test_rejects_handle_without_at(self):
        with pytest.raises(ValidationError):
            ChannelRef(yt_channel_id=None, handle="sebasi15", url="x")


class TestVideoStub:
    def test_minimal_flat_entry_short_without_duration(self):
        """FR-11 — 숏폼 flat 에는 duration 이 없다(TechSpike 3.1절). None 이 정상이다."""
        v = VideoStub(yt_video_id="QaZOH2zrUS8", kind=VideoKind.SHORT, title="제목", url="https://youtu.be/QaZOH2zrUS8")
        assert v.duration_s is None and v.view_count is None and v.thumbnail_url is None

    def test_kind_accepts_plain_string(self):
        v = VideoStub(yt_video_id=VID, kind="long", title="t", url="u", duration_s=996, view_count=16000)
        assert v.kind is VideoKind.LONG

    @pytest.mark.parametrize("bad_id", ["short", "L81RWsnY-vY1", "", "L81RWsnY v Y"])
    def test_rejects_bad_video_id(self, bad_id):
        with pytest.raises(ValidationError):
            VideoStub(yt_video_id=bad_id, kind=VideoKind.LONG, title="t", url="u")

    @pytest.mark.parametrize("title", ["", "   ", "\n\t"])
    def test_rejects_blank_title(self, title):
        with pytest.raises(ValidationError):
            VideoStub(yt_video_id=VID, kind=VideoKind.LONG, title=title, url="u")

    @pytest.mark.parametrize("field", ["duration_s", "view_count"])
    def test_rejects_negative_numbers(self, field):
        with pytest.raises(ValidationError):
            VideoStub(yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u", **{field: -1})

    def test_rejects_unknown_field(self):
        """FR-9 — extra=forbid: yt-dlp 응답을 **dict 로 넘겨 필드가 조용히 새는 것을 막는다."""
        with pytest.raises(ValidationError):
            VideoStub(yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u", uploader="x")

    def test_frozen(self):
        v = VideoStub(yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u")
        with pytest.raises(ValidationError):
            v.title = "바뀜"  # type: ignore[misc]

    def test_model_copy_update_produces_new_object(self):
        v = VideoStub(yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u")
        w = v.model_copy(update={"title": "새 제목"})
        assert w.title == "새 제목" and v.title == "t"


class TestVideo:
    def test_defaults_before_metadata_fetch(self):
        """FR-12 — 보충 전: upload_date/language 없음, transcript_status=none."""
        v = Video(yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u")
        assert v.upload_date is None and v.language is None and v.metadata_fetched_at is None
        assert v.transcript_status is TranscriptStatus.NONE

    def test_after_metadata_fetch(self):
        v = Video(
            yt_video_id=VID, kind=VideoKind.LONG, title="t", url="u", duration_s=995,
            upload_date=date(2026, 9, 11), language="ko", live_status="not_live",
            metadata_fetched_at=datetime(2026, 9, 14, 4, 0, tzinfo=UTC), transcript_status="pending",
        )
        assert v.upload_date.isoformat() == "2026-09-11"
        assert v.transcript_status is TranscriptStatus.PENDING

    def test_inherits_stub_rules(self):
        with pytest.raises(ValidationError):
            Video(yt_video_id="bad", kind=VideoKind.LONG, title="t", url="u")

    def test_is_a_video_stub(self):
        assert issubclass(Video, VideoStub)


class TestTranscriptSegment:
    def test_valid(self):
        s = seg(0, 359, 6680, " 지난 명절에 한우 드렸나요? ")
        assert s.text == "지난 명절에 한우 드렸나요?"  # strip 저장

    def test_zero_length_segment_allowed(self):
        assert seg(0, 100, 100).end_ms == 100

    def test_rejects_end_before_start(self):
        """FR-13 — 시간 역행은 파싱 오류의 징후다."""
        with pytest.raises(ValidationError):
            seg(0, 500, 499)

    @pytest.mark.parametrize("text", ["", "   ", "\n"])
    def test_rejects_blank_text(self, text):
        with pytest.raises(ValidationError):
            seg(0, 0, 10, text)

    @pytest.mark.parametrize(
        "kwargs",
        [{"idx": -1, "start_ms": 0, "end_ms": 1}, {"idx": 0, "start_ms": -5, "end_ms": 1}],
    )
    def test_rejects_negative_idx_or_start(self, kwargs):
        with pytest.raises(ValidationError):
            TranscriptSegment(text="x", **kwargs)


class TestTranscriptResult:
    def make(self, segments):
        return TranscriptResult(
            yt_video_id=VID, source=TranscriptSource.AUTO, language="ko", engine="yt-dlp",
            model_name=None, segments=segments,
        )

    def test_valid_and_derived(self):
        """FR-14 — full_text 는 세그먼트를 공백 하나로 결합, duration_ms 는 마지막 end."""
        r = self.make([seg(0, 0, 1000, "첫 문장"), seg(1, 1000, 2500, "둘째 문장")])
        assert r.full_text == "첫 문장 둘째 문장"
        assert r.duration_ms == 2500
        assert r.pipeline_version == PIPELINE_VERSION

    def test_whisper_result_carries_model_name(self):
        r = TranscriptResult(
            yt_video_id=VID, source="whisper", language="ko", engine="faster-whisper", model_name="small",
            segments=[seg(0, 0, 4300, "누군가에게나")],
        )
        assert r.source is TranscriptSource.WHISPER and r.model_name == "small"

    def test_rejects_empty_segments(self):
        with pytest.raises(ValidationError):
            self.make([])

    def test_rejects_non_contiguous_idx(self):
        """FR-14 — idx 가 0 부터 연속이 아니면 파서가 세그먼트를 빠뜨렸거나 섞었다."""
        with pytest.raises(ValidationError):
            self.make([seg(0, 0, 1), seg(2, 1, 2)])

    def test_rejects_idx_not_starting_at_zero(self):
        with pytest.raises(ValidationError):
            self.make([seg(1, 0, 1)])

    def test_rejects_decreasing_start(self):
        with pytest.raises(ValidationError):
            self.make([seg(0, 1000, 2000), seg(1, 500, 2500)])

    def test_equal_start_allowed(self):
        r = self.make([seg(0, 100, 200), seg(1, 100, 300)])
        assert len(r.segments) == 2

    def test_rejects_bad_video_id(self):
        with pytest.raises(ValidationError):
            TranscriptResult(yt_video_id="nope", source="auto", language="ko", engine="e", segments=[seg(0, 0, 1)])


class TestAnalysisModels:
    def test_analyzer_info(self):
        info = AnalyzerInfo(name="null", version="0", kinds=[], description="")
        assert info.kinds == []

    def test_analysis_result(self):
        r = AnalysisResult(
            yt_video_id=VID, analyzer_name="extractive", analyzer_version="1", kind=AnalysisKind.SUMMARY,
            language="ko", content={"summary": "요약"}, created_at=datetime(2026, 9, 14, tzinfo=UTC),
        )
        assert r.model_info == {} and r.content["summary"] == "요약"

    def test_analysis_result_rejects_unknown_kind(self):
        with pytest.raises(ValidationError):
            AnalysisResult(
                yt_video_id=VID, analyzer_name="x", analyzer_version="1", kind="translation",
                language="ko", content={}, created_at=datetime(2026, 9, 14, tzinfo=UTC),
            )
