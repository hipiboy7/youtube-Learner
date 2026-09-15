"""constants 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 1절, 요구사항 FR-6~FR-8."""

from __future__ import annotations

import re

import pytest

from youtube_learner import constants as c


class TestEnums:
    def test_video_kind_values(self):
        """FR-6 — 롱/숏/라이브 3값. 길이 기준 값은 없다(탭 소속 판정)."""
        assert {k.value for k in c.VideoKind} == {"long", "short", "live"}

    def test_transcript_source_values(self):
        """FR-6 — manual/auto/translated/whisper. translated 는 옵션이지만 값 집합은 P0 에서 닫는다."""
        assert {s.value for s in c.TranscriptSource} == {"manual", "auto", "translated", "whisper"}

    def test_transcript_status_values(self):
        assert {s.value for s in c.TranscriptStatus} == {"none", "pending", "done", "failed"}

    def test_analysis_kind_values(self):
        assert {k.value for k in c.AnalysisKind} == {"summary", "keypoints", "chapters"}

    def test_str_enum_behaves_as_plain_string(self):
        """FR-6 — StrEnum: DB·JSON·API 에 문자열 그대로 들어가야 한다."""
        assert c.VideoKind.LONG == "long"
        assert f"{c.VideoKind.SHORT}" == "short"
        assert c.TranscriptSource("whisper") is c.TranscriptSource.WHISPER

    def test_unknown_value_rejected(self):
        with pytest.raises(ValueError):
            c.VideoKind("clip")


class TestFixedValues:
    def test_original_caption_suffix(self):
        """FR-7 — yt-dlp 원어 자동자막 트랙 키 접미사 (TechSpike 3.2절)."""
        assert c.ORIGINAL_CAPTION_SUFFIX == "-orig"

    def test_lang_priority_default(self):
        assert c.LANG_PRIORITY_DEFAULT == ("ko",)
        assert isinstance(c.LANG_PRIORITY_DEFAULT, tuple)

    def test_pipeline_version_is_nonempty_string(self):
        assert isinstance(c.PIPELINE_VERSION, str) and c.PIPELINE_VERSION

    def test_db_filename(self):
        assert c.DB_FILENAME == "youtube_learner.db"

    def test_status_filename_pattern_uses_both_fields(self):
        assert c.STATUS_FILENAME_PATTERN.format(stage="sync", run_id="20260914-000000-deadbeef") == (
            "sync_20260914-000000-deadbeef.json"
        )

    @pytest.mark.parametrize("video_id", ["L81RWsnY-vY", "QaZOH2zrUS8", "___________", "a-b_c-d_e-f"])
    def test_video_id_pattern_accepts_real_ids(self, video_id):
        assert re.match(c.YT_VIDEO_ID_PATTERN, video_id)

    @pytest.mark.parametrize("bad", ["", "short", "L81RWsnY-vY1", "L81RWsnY-v!", "L81RWsnY-vY\n"])
    def test_video_id_pattern_rejects(self, bad):
        assert re.fullmatch(c.YT_VIDEO_ID_PATTERN, bad) is None

    def test_channel_id_pattern(self):
        assert re.match(c.YT_CHANNEL_ID_PATTERN, "UCgheNMc3gGHLsT-RISdCzDQ")
        assert re.match(c.YT_CHANNEL_ID_PATTERN, "@sebasi15") is None
        assert re.match(c.YT_CHANNEL_ID_PATTERN, "UCshort") is None

    def test_stage_name_pattern(self):
        assert re.match(c.STAGE_NAME_PATTERN, "sync_channel")
        assert re.match(c.STAGE_NAME_PATTERN, "Sync Channel") is None

    def test_package_name(self):
        assert c.PACKAGE_NAME == "youtube_learner"

    def test_manual_analysis_identity(self):
        """scope 2.4절 v1 수동 흐름 — 붙여 넣은 요약은 analyzer_name 'manual' / version 'user' 로 저장된다. null 과 겹치지 않는다."""
        assert c.MANUAL_ANALYZER_NAME == "manual" and c.MANUAL_ANALYZER_VERSION == "user"
        assert c.MANUAL_ANALYZER_NAME != "null"


class TestCaptionKey:
    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("ko-orig", ("ko", True)),
            ("ko", ("ko", False)),
            ("en-orig", ("en", True)),
            ("pt-BR", ("pt-BR", False)),
            ("zh-Hans-orig", ("zh-Hans", True)),
        ],
    )
    def test_split_caption_key(self, key, expected):
        """FR-8 — 'ko-orig' 는 원어, 'ko' 는 (원어가 아닐 수 있는) 일반 트랙."""
        assert c.split_caption_key(key) == expected

    @pytest.mark.parametrize("bad", ["", "   ", "-orig"])
    def test_split_caption_key_rejects_empty_or_bare_suffix(self, bad):
        with pytest.raises(ValueError):
            c.split_caption_key(bad)

    def test_original_caption_key(self):
        assert c.original_caption_key("ko") == "ko-orig"

    def test_original_caption_key_rejects_empty(self):
        with pytest.raises(ValueError):
            c.original_caption_key("")

    def test_roundtrip(self):
        assert c.split_caption_key(c.original_caption_key("ja")) == ("ja", True)
