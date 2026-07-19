class_name AnnouncerLines
## The announcer's vocabulary. Text-popup only for v1; a voice pass can key
## off the same tables later.

const DUNK: Array = [
	"BOOMSHAKALAKA!",
	"SLAM-A-JAMA!",
	"GRAVITY? NEVER MET HER!",
	"THE RIM IS FILING CHARGES!",
]
const THREE: Array = [
	"FROM DOWNTOWN!",
	"SPLASH!",
	"FROM THE PARKING LOT!",
	"RAINING BUCKETS!",
]
const GENERIC: Array = [
	"COUNT IT!",
	"BUCKETS.",
	"SILKY SMOOTH!",
	"CASH MONEY!",
]
const BLOCK: Array = [
	"REJECTED!",
	"GET THAT OUTTA HERE!",
	"NOT IN HER HOUSE!",
]
const STEAL: Array = [
	"PICKED HER POCKET!",
	"SWIPED!",
	"HANDS OF A FOX!",
]
const KNOCKDOWN: Array = [
	"FLATTENED!",
	"DOWN SHE GOES!",
]


static func pick(lines: Array, rng: RandomNumberGenerator) -> String:
	return lines[rng.randi() % lines.size()]
