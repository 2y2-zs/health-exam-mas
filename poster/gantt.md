# Gantt chart

The chart covers S1, the winter holiday and Semester 2. The **2027-02-05 Dissertation draft** is a project milestone for supervisor review. Dates with official deadlines are listed below with the time of day. Planned bars show target work windows.

```mermaid
gantt
    title PSP305 project plan
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    todayMarker off

    section S1 progress and submission
    Model 0 design and research scope revision :done, design, 2026-11-05, 2026-11-11
    Model 0 prototype and tests committed :done, milestone, checkpoint, 2026-11-20, 0d
    Prepare evidence, poster and five-minute video :poster, 2026-11-20, 2026-12-16
    Interim Poster official deadline :crit, milestone, interim, 2026-12-16, 0d

    section Winter holiday targets
    Confirm Model 1 data source and scope :data_plan, 2026-11-20, 2027-01-01
    Model 0 formal entry and verification :m0, 2026-12-17, 2027-01-01
    Model 1 FCFS baseline and checks :m1, after m0 data_plan, 17d
    Write introduction, literature review and methods :methods, 2026-12-17, 2027-01-18
    Run and interpret initial RQ2 comparisons :rq2, after m1, 8d
    Assemble complete Dissertation draft :assemble, after rq2 methods, 6d
    Review draft, figures and citations :review, after assemble, 4d
    Send draft to supervisor :milestone, draft, 2027-02-05, 0d

    section Semester 2
    Supervisor feedback and targeted follow-up :followup, 2027-02-22, 2027-03-22
    Prepare Oral Project Demonstration :demo_prep, after followup, 14d
    Oral Project Demonstration official deadline :crit, milestone, demo, 2027-04-05, 0d
    Revise Dissertation and check evidence :revision, 2027-04-06, 2027-05-09
    Dissertation official deadline :crit, milestone, final_due, 2027-05-09, 0d
```

## Milestones

| Date | Milestone |
| --- | --- |
| **2026-12-16 12:00** | Official Interim Poster and video deadline. |
| 2026-12-31 | Target for Model 0 verification and agreement on Model 1 data or the scope of a literature-based scenario. |
| 2027-01-25 | Target for first RQ2 results, after checking the Model 1 baseline and agreeing the comparison policy and experiment design. |
| 2027-01-31 | Target for a complete Dissertation draft with traceable results, sources and clearly stated limitations. |
| **2027-02-05** | Internal target to send the draft to the supervisor before Lunar New Year. |
| **2027-04-05 23:59** | Official Oral Project Demonstration deadline. |
| **2027-05-09 23:59** | Official Dissertation deadline. |

See [project progress](../PROJECT_PROGRESS.md) for evidence behind the completed work and [research context](../docs/RESEARCH_CONTEXT.md#schedule) for the official dates. If data access or verification delays the comparison, record the resulting scope change and base the draft on the evidence available.
