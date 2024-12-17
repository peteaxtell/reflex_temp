import polars as pl

GOALS_POINTS = {
    "Goalkeeper": 10,
    "Defender": 6,
    "Midfielder": 5,
    "Forward": 4
}

CLEAN_SHEET_POINTS = {
    "Goalkeeper": 4,
    "Defender": 4,
    "Midfielder": 1
}

SCORING_CONFIG = (
    # played 60 minutes
    {
        "filter": (pl.col("stats.minutes").gt(pl.col("stats.minutes_cache"))) & (pl.col("stats.minutes").gt(60)),
        "event": "Played 60 Minutes",
        "points": 1
    },
    # clean sheet
    {
        "filter": (pl.col("stats.clean_sheets").gt(pl.col("stats.clean_sheets_cache"))) & (pl.col("position_name").is_in(CLEAN_SHEET_POINTS.keys())),
        "event": "Clean Sheet",
        "points": pl.col("position_name").replace_strict(CLEAN_SHEET_POINTS).alias("points")
    },
    # goal scored
    {
        "filter": pl.col("stats.goals_scored").gt(pl.col("stats.goals_scored_cache")),
        "event": "Goal Scored",
        "points": pl.col("position_name").replace_strict(GOALS_POINTS).alias("points")
    },
    # goal assisted
    {
        "filter": pl.col("stats.assists").gt(pl.col("stats.assists_cache")),
        "event": "Goal Assisted",
        "points":  3
    },
    # penalty missed
    {
        "filter": pl.col("stats.penalties_missed").gt(pl.col("stats.penalties_missed_cache")),
        "event": "Penalty Missed",
        "points": -2
    },
    # own goal scored
    {
        "filter": pl.col("stats.own_goals").gt(pl.col("stats.own_goals_cache")),
        "event": "Own Goal Scored",
        "points": -2
    },
    # lost clean sheet
    {
        "filter": (pl.col("stats.clean_sheets").lt(pl.col("stats.clean_sheets_cache")) & (pl.col("position_name").is_in(CLEAN_SHEET_POINTS.keys()))),
        "event": "Lost Clean Sheet",
        "points":   pl.col("position_name").replace_strict(CLEAN_SHEET_POINTS).mul(-1).alias("points")
    },
    # 3 shots saved
    {
        "filter": (pl.col("stats.saves").gt(pl.col("stats.saves_cache"))) & (pl.col("stats.saves").mod(3).eq(0)),
        "event": "3 Shots Saved",
        "points":  1
    },
    # 2 goals conceded
    {
        "filter": (pl.col("stats.goals_conceded").gt(pl.col("stats.goals_conceded_cache"))) & (pl.col("stats.goals_conceded").mod(2).eq(0)),
        "event": "2 Goals Conceded",
        "points": -1
    },
    # penalty saved
    {
        "filter": pl.col("stats.penalties_saved").gt(pl.col("stats.penalties_saved_cache")),
        "event": "Penalty Saved",
        "points":  5
    },
    # yellow card
    {
        "filter": pl.col("stats.yellow_cards").gt(pl.col("stats.yellow_cards_cache")),
        "event": "Yellow Card",
        "points": -1
    },
    # red card
    {
        "filter": pl.col("stats.red_cards").gt(pl.col("stats.red_cards_cache")),
        "event": "Red Card",
        "points": -3
    },
    # bonus
    {
        "filter": pl.col("stats.bonus").gt(pl.col("stats.bonus_cache")),
        "event": "Bonus",
        "points": pl.col("stats.bonus").alias("points")
    },
)
