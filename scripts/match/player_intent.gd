class_name PlayerIntent
extends RefCounted
## One frame of control intent. Humans and AI both produce this and the sim
## consumes ONLY this — nothing in Baller/Ball reads Input directly. For the
## post-v1 netcode milestone these are the structs that get serialized.

var move := Vector2.ZERO  # direction on the floor plane, length <= 1
var turbo := false
var shoot_pressed := false  # offense: jump + charge shot / dunk. defense: block
var shoot_released := false  # release the shot (meter timing)
var pass_pressed := false  # offense: pass. defense: steal lunge
var switch_pressed := false  # human only: take nearest teammate to ball
var pass_target = null  # optional explicit receiver (AI); humans aim with move
