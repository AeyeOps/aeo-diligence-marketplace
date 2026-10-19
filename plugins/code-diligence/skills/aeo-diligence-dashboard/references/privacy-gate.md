# Working-pattern display setting

`heuristics.allow_working_pattern_card` defaults to false. The ingest and dashboard skills pass `--allow-working-pattern` only when the target settings enable it; the narrative workflow uses the same decision.

The renderer writes the flag into `src/data/config.json` in its temporary build project, alongside the target list. With the flag off, the Process page displays an opt-in notice and does not run the heatmap query or display its narrative. With the flag on, the chart aggregates commit counts by repository, weekday, and hour.

The setting controls display. The exported warehouse still contains the source commit records and timestamps. Decisions about enabling this view belong to the operator; the plugin adds no jurisdiction or approval rules.

The implementation lives in `src/code_diligence/settings/schema.py`, `src/code_diligence/dashboard/render.py`, and the Process page template. Keep this contract aligned with those files when behavior changes.
