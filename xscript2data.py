import random
import bpy
from bpy import *
import math
from math import *
import re
import mathutils
import threading, time
import xml.etree.ElementTree as ET
from pprint import pprint

linestart = {}
lineend = {}
abs_or_rel = "a"
rel_co = [0,0,0]
unfound_actions = []
unfound_face_actions = []
loc_dict = {}
rot_dict = {}
characters = []
character_data = []
errors_list = []
warnings_list = []
bezier_data = {}

class Struct: pass

def print_debug(*a):
	fout2 = open("/D/home/Blender/notes/print_debug.txt","a")
	fout2.write(" ".join([str(i) for i in a])+"\n")
	fout2.close()

def atleast1number(a):
	for i in a:
		if i >= "0" and i <= "9":
			return 1
	return 0

def extract_co(s):
	return [float(i) for i in re.split("\,|\;|\ ",re.match(r"\(?([^)]*)\)?",s).groups()[0]) if i != ""]

def extract_co_char(s):
	return [i for i in re.split("\,|\;|\ ",re.match(r"\(?(.*)\)?",s).groups()[0]) if i != ""]

def in_switch_set(c,s,t,f):
	if c in s:
		return t
	else:
		return f

def linenum_split(l):
	if "-:" in l:
		s = l.split("-:")
		return [s[0],"-:",s[1]]
	elif len(l) > 1 and l[0] == ":":
		return [":",":",l[1:]]
	elif ":" in l:
		s = l.split(":")
		return [s[0],":",s[1]]
	else:
		return ["","",l]

def subfind(t,s):
	l = []
	l.extend(t.findall(s))
	for i in t:
		l.extend(subfind(i,s))
	return l

def name_wo_num(n):
	j = -1
	while n[j] in "0123456789":
		j -= 1
	if n[j] == "." and n != -1:
		return n[:j]
	else:
		return n

def get_line_numbers(t): # t is a tree, in the format returned from xml_tree
	global linestart
	global lineend
	r = t.getroot()
	for j in r.findall("line"):
		sC = j.attrib["f"]
		eC = j.attrib["end"]
		n = j.attrib["n"]
		[s1,so,s2] = linenum_split(sC)
		if so == "-:":
			linestart[n] = lineend[s1] + int(s2)
		elif s1 == ":":
			linestart[n] = int(s2)
		elif so == ":":
			linestart[n] = linestart[s1] + int(s2)
		else:
			linestart[n] = int(s2)
		[s1,so,s2] = linenum_split(eC)
		if so == "-:":
			lineend[n] = lineend[s1] + int(s2)
		elif s1 == ":":
			lineend[n] = int(s2)
		elif so == ":":
			lineend[n] = linestart[s1] + int(s2)
		else:
			lineend[n] = linestart[n] + int(s2)

def calc_linenum(l,n): # l is the frame number in l:n format and n is the line number
	[s1,so,s2] = linenum_split(l)
	if s1 == ":" and so == ":":
		return int(s2)
	elif so == "" and s1 == "" and n != "":
		return linestart[n] + int(s2)
	elif so == "" and s1 == "" and n == "":
		return int(s2)
	elif s1 != "" and so == ":" and s2 != "":
		return linestart[s1] + int(s2)
	elif s1 != "" and so == "-:" and s2 != "":
		return lineend[s1] + int(s2)

def loc(a,e): # a = XML element; e = extra information (dictionary)
	global rel_co
	global abs_or_rel
	global errors_list
	actor = ""
	linenum = ""
	frameC = ""
	co = ""
	ar = abs_or_rel
	co_start = 0
	if "actor" in e and not("ch" in a.attrib):
		actor = e["actor"]
	elif "ch" in a.attrib:
		actor = a.attrib["ch"]
	if "line" in e:
		linenum = e["line"]
	if "f" in a.attrib:
		frameC = a.attrib["f"]
	else:
		errors_list.append("loc tag without 'f' attribute")
	if "co" in a.attrib:
		co = a.attrib["co"]
	else:
		errors_list.append("loc tag without 'co' attribute")
	if co[1] == "(":
		ar = co[0]
		co_start = 1
	co_num = extract_co(co[co_start:])
	if not(actor in loc_dict):
		loc_dict[actor] = {}
	frame = calc_linenum(frameC, linenum)
	loc_dict[actor][frame] = (ar,co_num[0],co_num[1],co_num[2])

def key_loc():
	global loc_dict
	global rel_co
	global abs_or_rel
	for actor in loc_dict.keys():
		(x1,y1,z1) = (0,0,0)
		ob = bpy.data.objects[actor]
		key_list = list(loc_dict[actor].keys())
		key_list.sort()
		for c in key_list:
			x0 = loc_dict[actor][c][1]
			y0 = loc_dict[actor][c][2]
			z0 = loc_dict[actor][c][3]
			c0 = loc_dict[actor][c][0]
			(x,y,z) = (0,0,0)
			if c0 == "a":
				x = x0
				y = y0
				z = z0
				(x1,y1,z1) = (x,y,z)
			if c0 == "r":
				x = x0 + rel_co[0]
				y = y0 + rel_co[1]
				z = z0 + rel_co[2]
				(x1,y1,z1) = (x,y,z)
			if c0 == "+":
				x = x1 + x0
				y = y1 + y0
				z = z1 + z0
				(x1,y1,z1) = (x,y,z)
			if c0 == "-":
				x = x1 - x0
				y = y1 - y0
				z = z1 - z0
				(x1,y1,z1) = (x,y,z)
			ob.location = (x,y,z)
			ob.keyframe_insert("location",frame=c)

def rot(a,e): # a = XML element; e = extra information (dictionary)
	actor = ""
	co = ""
	frameC = ""
	ar = "0"
	linenum = ""
	co_start = 0
	if "actor" in e and not("ch" in a.attrib):
			actor = e["actor"]
	elif "ch" in a.attrib:
		actor = a.attrib["ch"]
	if "line" in e:
		linenum = e["line"]
	if "f" in a.attrib:
		frameC = a.attrib["f"]
	else:
		errors_list.append("rot tag without 'f' attribute")
	if "co" in a.attrib:
		co = a.attrib["co"]
	else:
		errors_list.append("rot tag without 'co' attribute")
	if co[1] == "(":
		ar = co[0]
		co_start = 1
	co_num = extract_co(co[co_start:])
	if not(actor in rot_dict):
		rot_dict[actor] = {}
	frame = calc_linenum(frameC, linenum)
	rot_dict[actor][frame] = (ar,co_num[0],co_num[1],co_num[2])

def key_rot():
	global loc_dict
	global rel_co
	global abs_or_rel
	for actor in rot_dict.keys():
		(x1,y1,z1) = (0,0,0)
		ob = bpy.data.objects[actor]
		key_list = list(rot_dict[actor].keys())
		key_list.sort()
		for c in key_list:
			x0 = rot_dict[actor][c][1]
			y0 = rot_dict[actor][c][2]
			z0 = rot_dict[actor][c][3]
			c0 = rot_dict[actor][c][0]
			(x,y,z) = (0,0,0)
			if c0 == "+":
				x = x1 + x0
				y = y1 + y0
				z = z1 + z0
				(x1,y1,z1) = (x,y,z)
			if c0 == "-":
				x = x1 - x0
				y = y1 - y0
				z = z1 - z0
				(x1,y1,z1) = (x,y,z)
			else:
				x = x0
				y = y0
				z = z0
				(x1,y1,z1) = (x,y,z)
			ob.rotation_euler = (x*3.14159265/180,y*3.14159265/180,z*3.14159265/180)
			ob.keyframe_insert("rotation_euler",frame=c)

def act(a,e): # a = XML element; e = extra information (dictionary)
	global characters, errors_list, warnings_list
	actor = ""
	f1 = ""
	f2 = ""
	action = ""
	hold = 0
	blending = 0
	linenum = ""
	if "line" in e:
		linenum = e["line"]
	if "ch" in a.attrib:
		actor = a.attrib["ch"]
	elif "actor" in e:
		actor = e["actor"]
	if "a" in a.attrib:
		action = a.attrib["a"]
	else:
		errors_list.append("act tag without 'a' attribute")
	if "f" in a.attrib:
		if "," in a.attrib["f"]:
			[f1,f2] = a.attrib["f"].split(",")
		else:
			errors_list.append("'f' attribute of 'act' tag with one value  %s" % (" ".join([a.attrib["f"], action, actor]),))
	else:
		errors_list.append("act tag without 'f' attribute  %s" % (" ".join([action, actor]),))
	if "hold" in a.attrib:
		if a.attrib["hold"] == "forward":
			hold = 1
		elif a.attrib["hold"] == "both":
			hold = 2
	if "blending" in a.attrib:
		if a.attrib["blending"] == "add":
			blending = 1
		elif a.attrib["blending"] == "subtract":
			blending = 2
		elif a.attrib["blending"] == "multiply":
			blending = 3
	if actor in characters:
		arm = bpy.data.objects[actor + ".arm"]
	else:
		arm = bpy.data.objects[actor]
	arm0 = arm.data
	if action in bpy.data.actions and f1 != "" and f2 != "":
		action2 = bpy.data.actions[action]
		fn1 = calc_linenum(f1,linenum)
		fn2 = calc_linenum(f2,linenum)
		if arm.animation_data is None:
			arm.animation_data_create()
		nla = arm.animation_data.nla_tracks
		track = nla.new()
		track.name = action
		strip = track.strips.new(action,fn1,action2)
		if "use" in a.attrib:
			[use1,use2] = [int(i) for i in a.attrib["use"].split(",")]
			strip.action_frame_start = use1
			strip.action_frame_end = use2
		else:
			strip.action_frame_start = int(action2.frame_range[0])
			strip.action_frame_end = int(action2.frame_range[1])
		if "x" in a.attrib:
			strip.repeat = float(a.attrib["x"])
		strip.use_auto_blend = False
		if hold == 1:
			strip.extrapolation = "HOLD_FORWARD"
		elif hold == 2:
			strip.extrapolation = "HOLD"
		else:
			strip.extrapolation = "NOTHING"
		if blending == 1:
			strip.blend_type = "ADD"
		elif blending == 2:
			strip.blend_type = "SUBTRACT"
		elif blending == 3:
			strip.blend_type = "MULITPLY"
		else:
			strip.blend_type = "REPLACE"
		strip.frame_end = fn2
		if strip.action_frame_end != strip.action_frame_start:
			if (fn2-fn1)/(strip.repeat*(strip.action_frame_end-strip.action_frame_start)) >= 1000:
				r = (fn2-fn1)/(strip.repeat*(strip.action_frame_end-strip.action_frame_start))
				strip.repeat = 1+int(r/1000)
				strip.frame_end = fn2
				warnings_list.append("Action scale exceeds 1000: "+action+" "+actor+" "+str(linenum)+" "+str(r)+" "+str(strip.repeat))
		else:
			if (fn2-fn1)/strip.repeat >= 1000:
				r = (fn2-fn1)/strip.repeat
				strip.repeat = 1+int(r/1000)
				strip.frame_end = fn2
				warnings_list.append("Action scale exceeds 1000: "+action+" "+actor+" "+str(linenum)+" "+str(r)+" "+str(strip.repeat))
		if "b" in a.attrib:
			s = a.attrib["b"]
			b1C = ""
			b2C = ""
			[b1C,b2C] = a.attrib["b"].split(",")
			b1 = float(b1C)
			b2 = float(b2C)
			strip.blend_in = b1
			strip.blend_out = b2

def face(a,e):
	global characters
	global errors_list
	global warnings_list
	actor = ""
	f1 = ""
	f2 = ""
	action = ""
	hold = 0
	blending = 0
	linenum = ""
	if "line" in e:
		linenum = e["line"]
	if "ch" in a.attrib:
		actor = a.attrib["ch"]
	elif "actor" in e:
		actor = e["actor"]
	if "a" in a.attrib:
		action = a.attrib["a"]
	else:
		errors_list.append("face tag without 'a' attribute")
	if "f" in a.attrib:
		[f1,f2] = a.attrib["f"].split(",")
	else:
		errors_list.append("face tag without 'f' attribute")
	if "hold" in a.attrib:
		if a.attrib["hold"] == "forward":
			hold = 1
		elif a.attrib["hold"] == "both":
			hold = 2
	if "blending" in a.attrib:
		if a.attrib["blending"] == "add":
			blending = 1
		elif a.attrib["blending"] == "subtract":
			blending = 2
		elif a.attrib["blending"] == "multiply":
			blending = 3
	if actor in characters:
		arm = bpy.data.objects[actor + ".face"]
	else:
		arm = bpy.data.objects[actor]
	arm0 = arm.data
	if action in bpy.data.actions:
		action2 = bpy.data.actions[action]
		fn1 = calc_linenum(f1,linenum)
		fn2 = calc_linenum(f2,linenum)
		nla = arm.animation_data.nla_tracks
		track = nla.new()
		track.name = action
		strip = track.strips.new(action,fn1,action2)
		if "use" in a.attrib:
			[use1C,use2C] = a.attrib["use"].split(",")
			use1 = int(use1C)
			use2 = int(use2C)
			strip.action_frame_start = use1
			strip.action_frame_end = use2
		if hold == 1:
			strip.extrapolation = "HOLD_FORWARD"
		elif hold == 2:
			strip.extrapolation = "HOLD"
		else:
			strip.extrapolation = "NOTHING"
		if blending == 1:
			strip.blend_type = "ADD"
		elif blending == 2:
			strip.blend_type = "SUBTRACT"
		elif blending == 3:
			strip.blend_type = "MULITPLY"
		else:
			strip.blend_type = "REPLACE"
		if "add" in a and a["add"] == 1:
			strip.blend_type = "ADD"
		strip.use_auto_blend = False
		strip.frame_end = fn2
		if strip.action_frame_end != strip.action_frame_start:
			if (fn2-fn1)/(strip.repeat*(strip.action_frame_end-strip.action_frame_start)) >= 1000:
				r = (fn2-fn1)/(strip.repeat*(strip.action_frame_end-strip.action_frame_start))
				strip.repeat = 1+int(r/1000)
				strip.frame_end = fn2
				warnings_list.append("Action scale exceeds 1000: "+action+" "+actor+" "+str(linenum)+" "+str(r)+" "+str(strip.repeat))
		else:
			if (fn2-fn1)/strip.repeat >= 1000:
				r = (fn2-fn1)/strip.repeat
				strip.frame_end = fn2
				strip.repeat = 1+int(r/1000)
				warnings_list.append("Action scale exceeds 1000: "+action+" "+actor+" "+str(linenum)+" "+str(r)+" "+str(strip.repeat))
		if "b" in a.attrib:
			[b1C,b2C] = a.attrib["b"].split(",")
			b1 = int(b1C)
			b2 = int(b2C)
			strip.blend_in = b1
			strip.blend_out = b2

def characters_data(t): # t is XML tree with the characters tag as its root
	global characters, character_data, errors_list
	for i in t:
		character_data.append({})
		character_data[-1]["piece"] = {}
		name = i.find("name")
		if name == None:
			errors_list.append("Name tag is absent for a character")
		elif name.text == "":
			errors_list.append("Name tag for a character is empty")
		else:
			character_data[-1]["name"] = name.text
			characters.append(name.text)
		arm = i.find("arm")
		if arm != None and arm.text != "":
			character_data[-1]["arm"] = arm.text
		face = i.find("face")
		if face != None and face.text != "":
			character_data[-1]["face"] = face.text
		head = i.find("head")
		if head != None and head.text != "":
			character_data[-1]["head"] = head.text
		height = i.find("height")
		if height != None and height.text != "":
			character_data[-1]["height"] = float(height.text)
		group = i.find("group")
		if group != None and group.text != "":
			character_data[-1]["group"] = group.text
		for j in i.findall("piece"):
			character_data[-1]["piece"][j.attrib["suffix"]] = (j.text.strip(),[],j.attrib)
			for k in j.findall("material"):
				character_data[-1]["piece"][j.attrib["suffix"]][1].append((k.attrib["index"],k.attrib["name"]))
			

def relative(a):
	global abs_or_rel, rel_co, errors_list
	abs_or_rel = "r"
	c = ""
	if "co" in a.attrib:
		co = a.attrib["co"]
		rel_co = extract_co(co)
	else:
		abs_or_rel = "a"
		errors_list.append("relative tag without 'co' tag")

def curve(a):
	global abs_or_rel, rel_co
	loc_co = [0,0,0]
	loc_co_r = [0,0,0]
	rot_co = [0,0,0]
	size_co = [1,1,1]
	bpy.ops.object.add(type="CURVE")
	c = bpy.context.object
	c.name =  a.attrib["name"]
	if "loc" in a.attrib:
		a_loc = ""
		if a.attrib["loc"][0] == "a" or a["loc"][0] == "r":
			a_loc = a.attrib["loc"][1:]
		else:
			a_loc = a.attrib["loc"][:]
		loc_co = extract_co(a_loc)
		loc_co_r = loc_co[:]
		if abs_or_rel == "r" and a.attrib["loc"][0] == "r":
			for i in [0,1,2]:
				loc_co[i] += rel_co[i]
	if "rot" in a.attrib:
		rot_co = extract_co(a.attrib["rot"])
	if "size" in a.attrib:
		size_co = extract_co(a.attrib["size"])
	if a.attrib["type"] == "path":
		for i in a:
			pt1 = extract_co(i.text)
			pt2 = []
			if "ar" in i.attrib and i.attrib["ar"] == "a":
				pt2 = [pt1[0]-loc_co[0],pt1[1]-loc_co[1],pt1[2]-loc_co[2]]
			else:
				pt2 = [pt1[0]-loc_co_r[0] , pt1[1]-loc_co_r[1] , pt1[2]-loc_co_r[2]]
			eu = bpy.mathutils.Euler((rot_co[0] , rot_co[1] , rot_co[2]),"XYZ")
			rot_m = eu.to_matrix()
			v_loc = mathutils.vector((pt2[0],pt2[1],pt2[2]))
			pt2 = rot_m * v_loc
			pt3 = [pt2[0],pt2[1],pt2[2]]
			for i in range(3,len(pt1)):
				pt3.append(pt1[i])
			if len(c.data.splines) == 0:
				c.data.splines.new("NURBS")
			c.data.splines[-1].points.add(1)
			c.data.splines[-1].points[-1].co = mathutils.Vector((pt3[0],pt3[1],pt3[2],pt3[3]))
			c.data.splines[-1].points[-1].radius = pt3[4]
	elif a.attrib["type"] == "bezier":
		pass
	c.setFlag((c.getFlag() | 9)) # might subtract 1 from flag
	c[-1].setFlagU(c[-1].getFlagU() | 2)
	scn = Scene.GetCurrent()
	ob = scn.objects.new(c)
	pi180 = 180.0/3.14159265
	ob.location = (loc_co[0],loc_co[1],loc_co[2])
	ob.rotation_euler = (rot_co[0]/pi180,rot_co[1]/pi180,rot_co[2]/pi180)
	ob.scale = (size_co[0],size_co[1],size_co[2])

def gibberish(a,e):
	global linestart, lineend
	s = ""
	linenum = ""
	agent = ""
	if "f" in a.attrib:
		s = a.attrib["f"].split(",")
	if "line" in e:
		linenum = e["line"]
	if "actor" in e and not("ch" in a.attrib):
		agent = e["actor"]
	elif "ch" in a.attrib:
		agent = a.attrib["ch"]
	if agent in characters:
		arm = bpy.data.objects[agent + ".face"]
	else:
		arm = bpy.data.objects[agent]
	arm0 = arm.data
	saystart = calc_linenum(s[0], linenum)
	sayend = calc_linenum(s[1], linenum)
	s = saystart
	while s < sayend:
		vowell_num = int(random.random() * 12)
		r1 = int(random.random() * 10)
		r2 = int(random.random() * 10)
		sound_list = []
		vowell_list = [('a'),('e'),('i'),('o'),('u'),('A'),('E'),('I'),('O'),('U'),('O','E'),('a','U')]
		if r1 == 1 or r1 == 2:
			sound_list.append('m')
		if r1 == 3:
			sound_list.append('U')
		for i in vowell_list[vowell_num]:
			sound_list.append(i)
		if r2 == 1:
			sound_list.append('m')
		ii = 0
		nla = arm.animation_data.nla_tracks
		for i in sound_list:
			ActName = i
			fn1 = s + ii*6/len(sound_list) - 1
			fn2 = s + (ii+1)*6/len(sound_list)
			if ActName in bpy.data.actions:
				action = bpy.data.actions[ActName]
				track = nla.new()
				track.name = ActName
				strip = track.strips.new("Sound "+i,fn1,action)
				strip.action_frame_end = fn2-fn1
				strip.use_auto_blend = False
				strip.blend_in = 3
				strip.blend_out = 3
				strip.extrapolation = "NOTHING"
			else:
				global unfound_face_actions
				if ActName not in unfound_face_actions:
					unfound_face_actions.append(ActName)
			ii += 1
		s += 6

def clip(a,e):
	global errors_list
	actor = ""
	linenum = ""
	fC = ""
	startC = ""
	endC = ""
	if e != "" and "actor" in e and not("ch" in a.attrib):
		actor = e["actor"]
	elif "ch" in a:
		actor = a.attrib["ch"]
	if e != "" and "line" in e:
		linenum = e["line"]
	if "f" in a.attrib:
		fC = a.attrib["f"]
	else:
		errors_list.append("clip tag without 'f' attribute")
	if "s" in a.attrib:
		startC = a.attrib["s"]
	if "e" in a.attrib:
		endC = a.attrib["e"]
	ob = bpy.data.objects[actor]
	cam = ob.data
	if startC != "":
		cam.clip_start = float(startC)
		cam.keyframe_insert("clip_start",frame=calc_linenum(fC,linenum))
	if endC != "":
		cam.clip_end = float(endC)
		cam.keyframe_insert("clip_end",frame=calc_linenum(fC,linenum))

def multi(a,e):
	f = extract_co_char(a.find("frames").text)
	linenum = ""
	actor = ""
	if "line" in e:
		linenum = e["line"]
	if "actor" in e:
		actor = e["actor"]
	f1 = []
	for fi in f:
		f1.append(calc_linenum(fi,linenum))
	for j in a:
		if j.tag != "frames":
			actor2 = ""
			if "ch" in j.attrib:
				actor2 = j.attrib["ch"]
			else:
				actor2 = actor
			e2 = {}
			e2["actor"] = actor2
			e2["line"] = linenum
			for k in f:
				j.attrib["f"] = k
				make_data(j,e2)

def parent(a): # processes 'parent' xml tag
	global errors_list
	parent = ""
	child = ""
	if "p" in a.attrib:
		parent = a.attrib["p"]
	else:
		errors_list.append("parent tag without 'p' attribute")
	if "c" in a.attrib:
		child = a.attrib["c"]
	else:
		errors_list.append("parent tag without 'c' attribute")
	p_ob = bpy.data.objects[parent]
	c_ob = bpy.data.objects[child]
	c_ob.parent = p_ob

def make_childof_constraint(obj, parent_obj, name):
	constr = obj.constraints.new("CHILD_OF")
	constr.name = name
	constr.target = parent_obj
	return constr

def set_parent(obj, parent_obj):
	obj.parent = parent_obj

def prepare_parent(obj, parent_obj):
	obj.location = (0.0, 0.0, 0.0)
	obj.rotation_euler = (0.0, 0.0, 0.0)
	set_parent(obj, parent_obj)

def prepare_parent_if_none(obj, parent_obj):
	if obj.parent is None:
		prepare_parent(obj, parent_obj)

def constraint(a): # processes 'constraint' xml tag
	global errors_list
	if "type" in a.attrib:
		constr = None
		if a.attrib["type"] == "child_of":
			if "on" in a.attrib:
				o = bpy.data.objects[a.attrib["on"]]
				constr = o.constraints.new("CHILD_OF")
			else:
				errors_list.append("constraint tag without 'on' attribute")
			aa = a.find("loc")
			if aa != None:
				constr.use_location_x = in_switch_set("x",aa.text,True,False)
				constr.use_location_y = in_switch_set("y",aa.text,True,False)
				constr.use_location_z = in_switch_set("z",aa.text,True,False)
			aa = a.find("rot")
			if aa != None:
				constr.use_rotation_x = in_switch_set("x",aa.text,True,False)
				constr.use_rotation_y = in_switch_set("y",aa.text,True,False)
				constr.use_rotation_z = in_switch_set("z",aa.text,True,False)
			aa = a.find("scale")
			if aa != None:
				constr.use_scale_x = in_switch_set("x",aa.text,True,False)
				constr.use_scale_y = in_switch_set("y",aa.text,True,False)
				constr.use_scale_z = in_switch_set("z",aa.text,True,False)
		elif a.attrib["type"] == "follow_path": # more options need to be implemented
			if "on" in a.attrib:
				o = bpy.data.objects[a.attrib["on"]]
				constr = o.constraints.new("FOLLOW_PATH")
			else:
				errors_list.append("constraint tag without 'on' attribute")
			fw_a = a.find("fw")
			if fw_a != None:
				if fw_a.text == "x": constr.forward_axis = "FORWARD_X"
				elif fw_a.text == "y": constr.forward_axis = "FORWARD_Y"
				elif fw_a.text == "z": constr.forward_axis = "FORWARD_Z"
				elif fw_a.text == "-x": constr.forward_axis = "TRACK_NEGATIVE_X"
				elif fw_a.text == "-y": constr.forward_axis = "TRACK_NEGATIVE_Y"
				elif fw_a.text == "-z": constr.forward_axis = "TRACK_NEGATIVE_Z"
			up_a = a.find("up")
			if up_a != None:
				if up_a.text == "x": constr.up_axis = "UP_X"
				elif up_a.text == "y": constr.up_axis = "UP_Y"
				elif up_a.text == "z": constr.up_axis = "UP_Z"
			offset_a = a.find("offset")
			if offset_a != None:
				constr.offset = float(offset_a.text)
		if "name" in a.attrib:
			constr.name = a.attrib["name"]
		if "target" in a.attrib:
			constr.target = bpy.data.objects[a.attrib["target"]]
			if "bone" in a.attrib:
				constr.subtarget = a.attrib["bone"]
	else:
		errors_list.append("constraint tag without 'type' attribute")

def key(a,g):
	global errors_list
	linenum = ""
	if "line" in g:
		linenum = g["line"]
	if "type" in a.attrib:
		o = None
		if "on" in a.attrib and "name" in a.attrib and "f" in a.attrib and "i" in a.attrib:
			o = bpy.data.objects[a.attrib["on"]]
			constr = None
			for i in o.constraints:
				if i.name == a.attrib["name"]:
					constr = i
			constr.influence = float(a.attrib["i"])
			constr.keyframe_insert("influence",frame=calc_linenum(a.attrib["f"],linenum))
	else:
		errors_list.append("key tag without 'type' attribute")

def sound(t,g):
	if not bpy.context.scene.sequence_editor:
		bpy.context.scene.sequence_editor_create()
	if "f" in t.attrib and "path" in t.attrib:
		bpy.context.scene.sequence_editor.sequences.new_sound(t.attrib["path"], t.attrib["path"], 1, calc_linenum(t.attrib["f"],""))
	else:
		errors_list.append("sound tag without required attributes")

def input_data(t):
	if "type" in t.attrib and "name" in t.attrib and t.attrib["type"] == "bezier":
		global bezier_data
		bezier_data[t.attrib["name"]] = []
		for i in t:
			if i.tag == "tri":
				bezier_data[t.attrib["name"]].append([])
				for j in i:
					if j.tag == "i":
						bezier_data[t.attrib["name"]][-1].append(extract_co(j.text))

def modact(t,g):
	global characters, bezier_data, errors_list, warnings_list
	actor = ""
	SourceAct = ""
	NewAct = None
	if "name" in t.attrib:
		NewAct = t.attrib["name"]
	Armature = ""
	bones = []
	forth = []
	bezier = None
	if "data" in t.attrib:
		bezier = bezier_data[t.attrib["data"]]
	repeat = 1
	step = 0
	m_start = 1
	m_end = 1
	start = 1
	end = 1
	rot = [0.0,0.0,0.0]
	hold = 0
	blending = 0
	linenum = ""
	if "line" in g:
		linenum = g["line"]
	i = t.find("act")
	if i != None:
		if "ch" in i.attrib:
			actor = i.attrib["ch"]
		elif "actor" in g:
			actor = g["actor"]
		else:
			errors_list.append("modact without an actor")
		if "a" in i.attrib:
			SourceAct = i.attrib["a"]
		else:
			errors_list.append("act tag within modact without 'a' tag")
		if "f" in i.attrib:
			[m_start,m_end] = i.attrib["f"].split(",")
		else:
			errors_list.append("act tag within modact without 'f' tag")
		if "use" in i.attrib:
			[start,end] = i.attrib["use"].split(",")
		if "x" in i.attrib:
			repeat = int(i.attrib["x"])
		if "hold" in i.attrib:
			if i.attrib["hold"] == "forward":
				hold = 1
			elif i.attrib["hold"] == "both":
				hold = 2
		if "blending" in i.attrib:
			if i.attrib["blending"] == "add":
				blending = 1
			elif i.attrib["blending"] == "subtract":
				blending = 2
			elif i.attrib["blending"] == "multiply":
				blending = 3
	i = t.find("forth")
	if i != None:
		forth = extract_co(i.text)
	i = t.find("rot")
	if i != None:
		rot = extract_co(i.text)
	i = t.find("bones")
	if i != None:
		for j in i:
			bones.append(j.text)
	i = t.find("step")
	if i != None:
		step = int(i.text)
	if actor in characters:
		arm = bpy.data.objects[actor + ".arm"]
		Armature = actor + ".arm"
	else:
		arm = bpy.data.objects[actor]
		Armature = actor
	arm0 = arm.getData()
	MakeDeformedAction(SourceAct,NewAct,Armature,bones,forth,bezier,repeat,step,start,end,rot,10000)
	nla = arm.actionStrips
	if NewAct in bpy.data.actions:
		action2 = bpy.data.actions[NewAct]
		fn1 = calc_linenum(m_start,linenum)
		fn2 = calc_linenum(m_end,linenum)
		nla = arm.animation_data.nla_tracks
		track = nla.new()
		track.name = action
		strip = track.strips.new(action,fn1,action2)
		if blending == 1:
			strip.blend_type = "ADD"
		elif blending == 2:
			strip.blend_type = "SUBTRACT"
		elif blending == 3:
			strip.blend_type = "MULTIPLY"
		else:
			strip.blend_type = "REPLACE"
		if hold == 1:
			strip.extrapolation = "HOLD_FORWARD"
		elif hold == 2:
			strip.extrapolation = "HOLD"
		else:
			strip.extrapolation = "NOTHING"
		strip.use_auto_blend = False
		strip.frame_end = fn2
		if (fn2-fn1)/(strip.repeat*(strip.action_frame_end-strip.action_frame_start)) >= 1000: # Might want to avoid possible division by zero.
			warnings_list.append("WARNING: Action scale exceeds 1000"+str(action)+" "+str(actor)+" "+str(linenum))

def blending_modact(t,g):
	global errors_list
	act_tag_list = []
	bones = {}
	for i in t.findall("act"):
		act_tag_list.append(i.attrib)
		if "a" in i.attrib:
			action_list.append(bpy.data.actions[i.attrib["a"]])
		else:
			errors_list.append("act tag within modact tag without 'a' attribute")
	for i in t.findall("bone"):
		rank = 1
		method = "lrs"
		if "rank" in i.attrib:
			rank = int(i.attrib["rank"])
		if "method" in i.attrib:
			method = i.attrib["method"]
		bones[i.text] = (i.attrib["blending"],method,rank)
	for b in bones:
		pass

def bezier_length(co,delta):
	length = 0.0
	for i in range(len(co)-1):
		for j in range(delta):
			length += calc_dist_3d(bezier_get_pt(co,i+(j+0.0)/delta,0),bezier_get_pt(co,i+(j+1.0)/delta,0))
	return length

def bezier_get_pt(co,t,option):
	if option == 0:
		t0 = int(t)
		t1 = t-t0
		b = [0.0,0.0,0.0]
		if t >= len(co)-1.0:
			b = [co[-1][1][0],co[-1][1][1],co[-1][1][2]]
		else:
			for i in [0,1,2]:
				b[i] = (1-t1)**3*co[t0][1][i] + 3*(1-t1)**2*t1*co[t0][2][i] + 3*(1-t1)*t1**2*co[t0+1][0][i] + t1**3*co[t0+1][1][i]
		return b

def bezierPtFmLen(co,t,delta):
	length = 0.0
	i = 0
	j = 0
	end = 0
	while length < t and end == 0:
		if j >= delta:
			j = 0
			i += 1
		pt1 = bezier_get_pt(co,i+(j+0.0)/delta,0)
		pt2 = bezier_get_pt(co,i+(j+1.0)/delta,0)
		length += calc_dist_3d(pt1,pt2)
		j += 1
		if pt1[0] == co[-1][1][0] and pt1[1] == co[-1][1][1] and pt1[2] == co[-1][1][2]:
			end = 1
	return bezier_get_pt(co,i+(j+0.0)/delta,0)

def calc_dist_3d(a,b):
	return ( (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2 )**0.5

def bezierDer(co,dist,delta):
	length = 0.0
	i = 0
	j = 0
	end = 0
	while length < dist and end == 0:
		if j >= delta:
			j = 0
			i += 1
		pt1 = bezier_get_pt(co,i+(j+0.0)/delta,0)
		pt2 = bezier_get_pt(co,i+(j+1.0)/delta,0)
		length += calc_dist_3d(pt1,pt2)
		if pt1 == co[-1][1]:
			end = 1
		j += 1
	d = [0.0,0.0,0.0]
	t = i+(j+1.0)/delta
	t0 = int(t)
	t1 = t-t0
	if t0 < len(co)-1:
		for k in [0,1,2]:
			d[k] = -3*(1-t1)**2*co[t0][1][k] + (-6*(1-t1)*t1+3*(1-t1)**2)*co[t0][2][k] + (-3*t1**2+6*(1-t1)*t1)*co[t0+1][0][k] + 3*t1**2*co[t0+1][1][k]
		d = normalize(d)
	else:
		for k in [0,1,2]:
			# d[k] = 3*co[t0][1][k]
			d[k] = -3*(1-t1)**2*co[t0][1][k] + (-6*(1-t1)*t1+3*(1-t1)**2)*co[t0][2][k]
		d = normalize(d)
	return d

def normalize(v):
	sum = 0.0
	for i in v:
		sum += i**2
	w = []
	for i in v:
		w.append(i/sum**0.5)
	return w

def GetRotationMatrix(angle,axis):
	M = [ [0,0,0] , [0,0,0] , [0,0,0] ]
	t = angle
	M[0][0] = cos(t)+axis[0]**2*(1-cos(t))
	M[0][1] = axis[0]*axis[1]*(1-cos(t))-axis[2]*sin(t)
	M[0][2] = axis[1]*axis[2]*(1-cos(t))-axis[1]*sin(t)
	M[1][0] = axis[1]*axis[0]*(1-cos(t))-axis[2]*sin(t)
	M[1][1] = cos(t)+axis[1]**2*(1-cos(t))
	M[1][2] = axis[1]*axis[2]*(1-cos(t))-axis[0]*sin(t)
	M[2][0] = axis[2]*axis[0]*(1-cos(t))-axis[1]*sin(t)
	M[2][1] = axis[2]*axis[1]*(1-cos(t))-axis[2]*sin(t)
	M[2][2] = cos(t)+axis[2]**2*(1-cos(t))
	matrix = mathutils.Matrix((M[0],M[1],M[2]))
	return matrix

def deform_pt(orig,move,forth,bezier,delta):
	forthV = mathutils.Vector((forth[0],forth[1],forth[2]))
	moveOffsetV = mathutils.Vector((move[0]-orig[0],move[1]-orig[1],move[2]-orig[2]))
	dist = moveOffsetV.project(forthV).magnitude
	CurvePivot = bezierPtFmLen(bezier,dist,delta)
	CurvePivotV = mathutils.Vector((CurvePivot[0],CurvePivot[1],CurvePivot[2]))
	bezierOriginV = mathutils.Vector((bezier[0][1][0],bezier[0][1][1],bezier[0][1][2]))
	moveV = mathutils.Vector((move[0],move[1],move[2]))
	Deform1 = moveV - dist*forthV
	der = bezierDer(bezier,dist,delta)
	derV = mathutils.Vector((der[0],der[1],der[2]))
	angle = -derV.angle(forthV,0.0)
	axis = forthV.cross(derV)
	if not(axis[0] == 0.0 and axis[1] == 0.0 and axis[2] == 0.0):
		axis.normalize()
	RotMat = GetRotationMatrix(angle,axis)
	Deform2 = RotMat*Deform1
	return [(Deform2+CurvePivotV),derV]

def MakeDeformedAction(SourceAct,NewAct,Armature,bones,forth,bezier,repeat,step,start,end,rot,delta):
	bezier2 = []
	RotMatrix = mathutils.Euler((rot[0],rot[1],rot[2]),"XZY").to_matrix()
	origV = mathutils.Vector((bezier[0][1][0],bezier[0][1][1],bezier[0][1][2]))
	for b in bezier:
		bezier2.append([])
		for i in b:
			cur_coV = mathutils.Vector((i[0],i[1],i[2]))
			new_co = RotMatrix*(cur_coV-origV)+origV
			bezier2[-1].append([new_co[0],new_co[1],new_co[2]])
	MakeDeformedAction2(SourceAct,NewAct,Armature,bones,forth,bezier2,repeat,step,start,end,delta)

def MakeDeformedAction2(SourceAct,NewAct,Armature,bones,forth,bezier,repeat,step,start,end,delta):
	armO = bpy.data.objects[Armature]
	arm = armO.data
	act = bpy.data.actions[SourceAct]
	a = bpy.data.actions.new(NewAct)
	armO.animation_data.action = a
	forthV = mathutils.Vector((forth[0],forth[1],forth[2]))
	framesize = end-start+1
	for b in bones:
		BoneMatrix = arm.bones[b].matrix_local.to_3x3()
		BoneMatrix1 = BoneMatrix.inverted()
		orig = arm.bones[b].head_local
		fcurves = []
		for f in act.fcurves:
			if f.group.name == b:
				fcurves.append(f)
		frames = getFCurveFrames(fcurves)
		frames2 = []
		for f in frames:
			if f >= start and f <= end:
				frames2.append(int(f))
		if not(start in frames2):
			frames2.append(start)
		if not(end in frames2):
			frames2.append(end)
		for r in range(repeat):
			for f in frames2:
				(LocX,LocY,LocZ) = (0,0,0)
				(x,y,z) = (0,0,0)
				for i in fcurves:
					if i.data_path[-8:] == "location" and i.array_index == 0: LocX = i
					if i.data_path[-8:] == "location" and i.array_index == 1: LocY = i
					if i.data_path[-8:] == "location" and i.array_index == 2: LocZ = i
				if LocX != 0: x = LocX.evaluate(f)
				if LocY != 0: y = LocY.evaluate(f)
				if LocZ != 0: z = LocZ.evaluate(f)
				move = BoneMatrix*mathutils.Vector((x,y,z))+orig+step*r*forthV
				new_co = deform_pt(orig,move,forth,bezier,delta)
				pose = armO.pose
				new_co1 = BoneMatrix*(new_co[0]-orig)
				pose.bones[b].location = [new_co1[0],new_co1[1],new_co1[2]]
				bpy.ops.anim.change_frame(frame=int(f)+r*framesize-start+1)
				pose.bones[b].keyframe_insert("location",frame=int(f)+r*framesize-start+1)
				angle = -new_co[1].angle(forthV,0.0)
				axis = forthV.cross(new_co[1])
				axis.normalize()
				RotMat = GetRotationMatrix(angle,axis)
				(RotW,RotX,RotY,RotZ) = (0,0,0,0)
				(w,x,y,z) = (0,0,0,0)
				for i in fcurves:
					if i.data_path[-10:] == "quaternion" and i.array_index == 0: RotW = i
					if i.data_path[-10:] == "quaternion" and i.array_index == 1: RotX = i
					if i.data_path[-10:] == "quaternion" and i.array_index == 2: RotY = i
					if i.data_path[-10:] == "quaternion" and i.array_index == 3: RotZ = i
				if RotW != 0: w = RotW.evaluate(f)
				if RotX != 0: x = RotX.evaluate(f)
				if RotY != 0: y = RotY.evaluate(f)
				if RotZ != 0: z = RotZ.evaluate(f)
				new_mat = RotMat*mathutils.Quaternion((w,x,y,z)).to_matrix()
				new_euler = new_mat.to_euler("XZY")
				new_euler2 = BoneMatrix*mathutils.Vector((new_euler[0],new_euler[1],new_euler[2]))
				new_quat = mathutils.Euler((new_euler2[0],new_euler2[1],new_euler2[2]),"XZY").to_quaternion()
				pose.bones[b].rotation_quaternion = [new_quat[0],new_quat[1],new_quat[2],new_quat[3]]
				bpy.ops.anim.change_frame(frame=int(f)+r*framesize-start+1)
				pose.bones[b].keyframe_insert("rotation_quaternion",frame=int(f)+r*framesize-start+1)

def MakeMatrix(f):
	M = 0
	if len(f) == 16:
		M = mathutils.Matrix(((f[0],f[1],f[2],f[3]),(f[4],f[5],f[6],f[7]),(f[8],f[9],f[10],f[11]),(f[12],f[13],f[14],f[15])))
	if len(f) == 9:
		M = mathutils.Matrix(((f[0],f[1],f[2]),(f[3],f[4],f[5]),(f[6],f[7],f[8])))
	return M

def getFCurveFrames(fcurves):
	frames = []
	for f in fcurves:
		for k in f.keyframe_points:
			if not(k.co[0] in frames):
				frames.append(k.co[0])
	frames.sort()
	return frames

def get_actions_list(t):
	action_list = []
	face_list = []
	r = t.getroot()
	c = r.find("characters")
	if characters != None:
		characters_data(c)
	actions = subfind(r,"act")
	for a in actions:
		if "a" in a.attrib and not(a.attrib["a"] in action_list):
			action_list.append(a.attrib["a"])
	face_actions = r.findall("face")
	for i in r:
		if i.tag != "characters":
			face_actions.extend(subfind(i,"face"))
	for f in face_actions:
		if "a" in f.attrib and not(f.attrib["a"] in action_list):
			face_list.append(f.attrib["a"])
	return (action_list,face_list)

def get_props(t,theType):
	global errors_list
	prop_list = []
	group_list = []
	props_tag = t.find(theType)
	if props_tag is not None:
		for p in props_tag:
			name = p.find("name")
			if name is not None:
				prop_list.append(name.text)
			group = p.find("group")
			if group is not None:
				group_list.append(group.text)
			if name is None and group is None:
				errors_list.append("prop without a name or group")
	return (prop_list, group_list)

def deselect_context_objects():
	for o in bpy.context.selected_objects:
		o.select_set(state=False)

def format_object_name(obj, cname, extension):
	obj.name = cname + "." + extension

def get_object_named(name, objlist):
	for i in objlist:
		if i.name == name:
			return i

def set_modifier_targets(recently_loaded,arm,face):
	for i in recently_loaded:
		if type(i.data) == bpy.types.Mesh:
			for j in i.modifiers:
				if j.type == "HOOK":
					if j.object is None or "arm" in j.object.name.lower():
						j.object = arm
					elif "face" in j.object.name.lower():
						j.object = face
				if j.type == "ARMATURE":
					if j.object is None or "arm" in j.object.name.lower():
						j.object = arm
					elif "face" in j.object.name.lower():
						j.object = face
				if j.type == "LATTICE":
					name = name_wo_num(j.object.name)
					rest = name[name.find(".")+1:]
					j.object = bpy.data.objects[i.name.split(".")[0]+"."+rest]

def make_piece_modifiers(pieceOb, name):
	charOb = bpy.data.objects[name + ".head"]
	for i in charOb.modifiers:
		if hasattr(i,"vertex_group") and getattr(i,"vertex_group") in [j.name for j in pieceOb.vertex_groups]:
			newMod = pieceOb.modifiers.new(i.name,i.type)
			for j in ("object","subtarget","vertex_group"):
				if hasattr(newMod,j):
					setattr(newMod,j,getattr(i,j))
				print("PIECE MODIFIERS 1", newMod, i, j, getattr(i,j))
	bpy.context.view_layer.objects.active = pieceOb
	print([i.name for i in pieceOb.modifiers])
	while pieceOb.modifiers.find("Subdivision") not in (len(pieceOb.modifiers)-1, -1):
		bpy.ops.object.modifier_move_down(modifier="Subdivision")
		#print("PIECE MODIFIERS MOVE SUBSURF")
	while pieceOb.modifiers.find("Armature") not in (len(pieceOb.modifiers)-2, -2):
		bpy.ops.object.modifier_move_down(modifier="Armature")
		#print("PIECE MODIFIERS MOVE ARMATURE")

def reset_hooks(obj):
	bpy.context.view_layer.objects.active = obj
	if obj.type == "MESH":
		bpy.ops.object.mode_set(mode="EDIT")
		for m in obj.modifiers:
			if m.type == "HOOK":
				bpy.ops.object.hook_reset(modifier=m.name)
		bpy.ops.object.mode_set(mode="OBJECT")

def get_objects_to_load(filename, objects_to_find):
	# http://blenderartists.org/forum/showthread.php?248493-Loading-Libraries
	objects_to_load = []
	with bpy.data.libraries.load(filename) as (src, _):
		try:
			for obj in src.objects:
				results = [{'name':obj} for obj in src.objects]
		except UnicodeDecodeError as detail:
			print(detail)
		for obj in results:
			if obj.get('name') in objects_to_find:
				objects_to_load.append(obj)
			elif wildcard_match_list(obj["name"],objects_to_find):
				objects_to_load.append(obj)
	return objects_to_load

def load_objects(filename, objects_to_find):
	print("LOAD OBJECTS FUNCTION", filename, objects_to_find)
	obj_list = get_objects_to_load(filename, objects_to_find)
	print("OBJ_LIST = ", obj_list)
	if obj_list != []:
		bpy.ops.wm.append(directory=filename + '/Object/', autoselect=True, files=obj_list)
	return bpy.context.selected_objects

def make_armature_modifier(piece_data, main_object, arm): #if "with" not in c["piece"][i][2] or c["piece"][i][2]["with"] == "reset":
	print("PIECE DATA", piece_data, main_object, arm)
	if "with" not in piece_data[2] or piece_data[2] == "reset":
		if len([k for k in main_object.modifiers if k.type == "ARMATURE"]) == 0:
			mod = main_object.modifiers.new("Armature","ARMATURE")
			mod.object = arm
		else:
			for i in [k for k in main_object.modifiers if k.type == "ARMATURE"]:
				i.object = arm

def get_main_pieces(objlist, name):
	j = -1
	arm = None; face = None; head = None
	while -j <= len(objlist):
		if objlist[j].type == "ARMATURE":
			if name_wo_num(objlist[j].name)[-4:] == ".arm":
				arm = objlist[j]
			elif name_wo_num(objlist[j].name)[-5:] == ".face":
				face = objlist[j]
		elif name_wo_num(objlist[j].name) == name:
			head = objlist[j]
			head.name = name + ".head"
		j -= 1
	return (head, arm, face)

def load_group(groupName, filePath):
	bpy.ops.wm.append(filename=groupName, directory=filePath+"/Collection/")

def make_empty_for_character(name, height, x):
	bpy.ops.object.add(type="EMPTY", location=(x,0.0,-10.0), rotation=(0.0,0.0,0.0))
	empty = bpy.context.object
	empty.name = name
	empty.scale = (height/8, height/8, height/8)
	return empty

def find_piece_key(c, name):
	for i in c["piece"]:
		if name == name_wo_num(name) and name_wo_num(c["piece"][i][0]) == name:
			return i

def load_pieces_for_character(c, pfile, arm, empty):
	new_objects = load_objects(pfile, [c["piece"][i][0] for i in c["piece"]])
	print("LOAD PIECES FOR CHARACTER", new_objects, type(new_objects))
	for o in new_objects:
		i = find_piece_key(c, o.name)
		print("object", i, o.name)
		if i is not None:
			o.name = c["name"] + "." + i
			prepare_parent_if_none(o, empty)
			print("LINE 1291", i, o.name, c)
			make_armature_modifier(c["piece"][i], o, arm)
			for k in c["piece"][i][1]:
				bpy.ops.wm.append(directory=pfile+'/Material/', files=[{"name":k[1]}])
				o.data.materials[int(k[0])] = bpy.data.materials[k[1]]
			make_piece_modifiers(o, c["name"])
	deselect_context_objects()
	return new_objects

def load_actions(afile, ffile, act_list, face_list):
	with bpy.data.libraries.load(afile) as (src, _):
		actlist = []
		try:
			acts_to_load = [{'name':act} for act in src.actions]
		except UnicodeDecodeError as detail:
			print(detail)
		for act in acts_to_load:
			if act.get('name') in act_list:
				actlist.append(act)
	with bpy.data.libraries.load(ffile) as (src, _):
		facelist = []
		try:
			faces_to_load = [{'name':face} for face in src.actions]
		except UnicodeDecodeError as detail:
			print(detail)
		for face in faces_to_load:
			if face.get('name') in face_list:
				facelist.append(face)
	if actlist != []:
		bpy.ops.wm.append(directory=afile + '/Action/', autoselect=True, files=actlist)
	if facelist != []:
		bpy.ops.wm.append(directory=ffile + '/Action/', autoselect=True, files=facelist)
	all_action_names = [bpy.data.actions[i].name for i in range(len(bpy.data.actions))]
	for i in act_list:
		if not(i in all_action_names):
			unfound_actions.append(i)
	for i in face_list:
		if not(i in all_action_names):
			unfound_face_actions.append(i)

def add_to_collection(obj, collection_name):
	if collection_name in bpy.data.collections:
		if obj.name not in bpy.data.collections[collection_name].all_objects:
			bpy.data.collections[collection_name].objects.link(obj)

def load_objects_from_data(cfile,pfile,characters_list):
	global unfound_actions, unfound_face_actions, errors_list
	scn = bpy.context.scene
	x = 0.0 # x-coordinate where object will be placed in the scene (overridden by location keyframes)
	print("BEGIN LOADING DATA")
	for c in characters_list: # each 'c' is a dictionary of character data
		# keys in 'c' could be: 'name', 'group', 'height', 'piece'
		# If the key is 'piece' its value is a dictionary
		# Keys 'group' and 'name' are string values; 'height' is float value
		print("LOADING DATA FOR CHARACTER", c)
		recently_loaded = []; keep_loaded = []; reset_pieces = []; file_objs = []
		arm = None; face = None; head = None
		height = float(c["height"]) if "height" in c else 8
		name = c["name"]
		empty = make_empty_for_character(name, height, x)
		deselect_context_objects()
		if "group" in c:
			load_group(c["group"], cfile)
			recently_loaded.extend(bpy.context.selected_objects)
			keep_loaded.extend(bpy.context.selected_objects)
			(head, arm, face) = get_main_pieces(bpy.context.selected_objects, c["group"])
			for o in bpy.context.selected_objects:
				if o.parent is None:
					prepare_parent(o, empty)
				add_to_collection(o, name)
		else:
			new_objects = load_objects(cfile, [name, name+".arm", name+".face"]).objects
			keep_loaded.extend(new_objects)
			if new_objects == []:
				errors_list.append("Error: Object named " + str(c.get(i[0])) + " was not found")
			else:
				for i in new_objects:
					prepare_parent(i, empty)
					add_to_collection(i, name)
				(head, arm, face) = get_main_pieces(new_objects, name)
				set_modifier_targets(recently_loaded, arm, face)
		add_to_collection(empty, name)
		deselect_context_objects()
		pieces = load_pieces_for_character(c, pfile, arm, empty)
		set_modifier_targets(pieces, arm, face)
		recently_loaded.extend(pieces)
		keep_loaded.extend(pieces)
		if head is not None and arm is not None:
			align_eye_bones(arm,head)
		for i in recently_loaded:
			reset_hooks(i)
		x += 2.0
		deselect_context_objects()
	# Delete extra objects
	to_delete = []
	for i in recently_loaded:
		if i not in keep_loaded:
			to_delete.append(i)
	print("RECENTLY LOADED", recently_loaded)
	print("TO KEEP", keep_loaded)
	print("TO DELETE", to_delete)
	for i in to_delete:
		i.select_set(state=True)
	bpy.ops.object.delete()

def copy_drivers(new_object,object_name,file,armature):
	with bpy.data.libraries.load(file) as (lister,getter):
		obs = getattr(lister,"objects")
		getter.objects.append(object_name)
	o = getter.objects[0]
	drivers = o.data.shape_keys.animation_data.drivers
	new_object.data.shape_keys.animation_data_create()
	for d in drivers:
		pass

def align_eye_bones(arm,head):
	arm0 = arm.data
	head0 = head.data
	left_eye = head.vertex_groups["Eye.L"]
	right_eye = head.vertex_groups["Eye.R"]
	left_vertices = get_vertices_from_group(head,left_eye.index)
	right_vertices = get_vertices_from_group(head,right_eye.index)
	left_center = left_vertices[0]
	right_center = right_vertices[0]
	left_top = left_vertices[0]
	right_top = right_vertices[0]
	left_bottom = left_vertices[0]
	right_bottom = right_vertices[0]
	for v in left_vertices:
		if head0.vertices[v].co[1] < head0.vertices[left_center].co[1]:
			left_center = v
		if head0.vertices[v].co[2] < head0.vertices[left_bottom].co[2]:
			left_bottom = v
		if head0.vertices[v].co[2] > head0.vertices[left_top].co[2]:
			left_top = v
	for v in right_vertices:
		if head0.vertices[v].co[1] < head0.vertices[right_center].co[1]:
			right_center = v
		if head0.vertices[v].co[2] < head0.vertices[right_bottom].co[2]:
			right_bottom = v
		if head0.vertices[v].co[2] > head0.vertices[right_top].co[2]:
			right_top = v
	size = head.scale[2]
	left_top0 = head0.vertices[left_top].co
	left_bottom0 = head0.vertices[left_bottom].co
	left_center0 = head0.vertices[left_center].co
	bpy.context.view_layer.objects.active = arm
	bpy.ops.object.mode_set(mode='EDIT')
	head_tail = arm0.edit_bones["Head"].tail
	arm0.edit_bones["Eye.L"].use_local_location = True
	arm0.edit_bones["Eye.L"].head = mathutils.Vector([left_bottom0[0]*size,left_top0[1]*size,(left_bottom0[2]+left_top0[2])/2.0*size])
	arm0.edit_bones["Eye.L"].tail = mathutils.Vector([left_center0[0]*size,left_center0[1]*size,left_center0[2]*size])
	right_top0 = head0.vertices[right_top].co
	right_bottom0 = head0.vertices[right_bottom].co
	right_center0 = head0.vertices[right_center].co
	arm0.edit_bones["Eye.R"].use_local_location = True
	arm0.edit_bones["Eye.R"].head = mathutils.Vector([right_bottom0[0]*size,right_top0[1]*size,(right_bottom0[2]+right_top0[2])/2.0*size])
	arm0.edit_bones["Eye.R"].tail = mathutils.Vector([right_center0[0]*size,right_center0[1]*size,right_center0[2]*size])
	bpy.ops.object.mode_set(mode='OBJECT')

def get_vertices_from_group(a,index):
	# a is a Blender object 
	# index is an integer representing the index of the vertex group in a
	vlist = []
	for v in a.data.vertices:
		for g in v.groups:
			if g.group == index:
				vlist.append(v.index)
	return vlist

def load_object_groups(filename, groupList):
	print_debug("GROUP LIST" + str(groupList))
	print_debug("filename:", filename)
	for i in groupList:
		print_debug("load group iteration", i)
		bpy.ops.wm.append(directory=filename+"/Collection/", filename=i)
		print_debug("GROUP LIST 2", [i.name for i in bpy.data.objects])

def wildcard_match_list(o,l):
	if l == []:
		return False
	for i in l:
		if wildcard_match(o,i):
			return True
	return False

def wildcard_match(o,i):
	i0 = i.replace(".","\.")
	i1 = i0.replace("*",".")
	i2 = re.compile(i1)
	return re.match(i2,o)

def make_data(t,g): # t is an XML tree and g is a dictionary of extra information
		global errors_list
		if t.tag == "xscript":
			for t0 in t:
				make_data(t0,{})
		if t.tag == "relative":
			relative(t)
		if t.tag == "line":
			line = None
			actor = None
			if "n" in t.attrib:
				line = t.attrib["n"]
			else:
				errors_list.append("line tag without 'n' attribute")
			if "a" in t.attrib:
				actor = t.attrib["a"]
			else:
				errors_list.append("line tag without 'a' attribute")
			for t0 in t:
				g1 = {}
				g1["line"] = line
				g1["actor"] = actor
				make_data(t0,g1)
		if t.tag == "loc":
			loc(t,g)
		if t.tag == "rot":
			rot(t,g)
		if t.tag == "act":
			act(t,g)
		if t.tag == "face":
			face(t,g)
		if t.tag == "gibberish":
			gibberish(t,g)
		if t.tag == "curve":
			curve(t)
		if t.tag == "clip":
			clip(t,g)
		if t.tag == "multi":
			multi(t,g)
		if t.tag == "parent":
			parent(t)
		if t.tag == "constraint":
			constraint(t)
		if t.tag == "key":
			key(t,g)
		if t.tag == "data":
			input_data(t)
		if t.tag == "modact":
			modact(t,g)
		if t.tag == "sound":
			sound(t,g)

def xscript2data(f,l):
	global characters, character_data, errors_list, warnings_list
	x = ET.parse(f)
	get_line_numbers(x)
	(act_list,face_list) = get_actions_list(x)
	print(act_list)
	face_list.extend(['A','E','I','O','U','a','e','i','o','u','m'])
	theProps = get_props(x,"props")
	bgProps = get_props(x,"background")
	load_objects(l[3],theProps[0])
	print_debug("load_objects(l[3],theProps[0])", l[3], theProps[0])
	load_objects(l[4],bgProps[0])
	print_debug("load_objects(l[4],bgProps[0])", l[4], bgProps[0])
	load_object_groups(l[3],theProps[1])
	print_debug("load_object_groups(l[3],theProps[1])", l[3],theProps[1])
	load_object_groups(l[4],bgProps[1])
	print_debug("AFTER LOAD PROPS")
	print_debug("load_object_groups(l[4],bgProps[1])", l[4], bgProps[1])
	print_debug(theProps)
	print_debug(bgProps)
	load_objects_from_data(l[0],l[5],character_data)
	load_actions(l[1],l[2], act_list, face_list)
	make_data(x.getroot(),{})
	key_loc()
	key_rot()
	print("linestart")
	pprint(linestart)
	print("lineend")
	pprint(lineend)
	print("Unfound actions: ", unfound_actions)
	print("Unfound face actions: ", unfound_face_actions)
	for i in errors_list:
		print("ERROR: "+i)
	for i in warnings_list:
		print("WARNING: "+i)

def loadLibraries():
	lib = [None]*6
	lib_file = open("/D/home/Blender/python/xscript_libraries.txt","r")
	lib_order = {"characters":0,"actions":1,"face":2,"props":3,"background":4,"clothes":5}
	for i in lib_file:
		if i[0] != "#" and i.strip() != "":
			j = i.split("=")
			if j[0] in lib_order:
				lib[lib_order[j[0]]] = j[1].strip()
	return lib

class PANEL_PT_xscriptpanel(bpy.types.Panel):
	bl_idname = "PANEL_PT_xscriptpanel"
	bl_label = "xscript"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

	def __init__(self):
		self.scn = bpy.context.scene

	def draw(self,context):
		layout = self.layout
		layout.prop(self.scn,"directory")
		layout.prop(self.scn,"file")
		layout.operator("data.load", text="Load")

class DATA_OT_load(bpy.types.Operator):
	global lib_list
	bl_idname = "data.load"
	bl_label = "Load"
	def execute(self,context):
		fullpath = getattr(bpy.context.scene,"directory") + getattr(bpy.context.scene,"file")
		fh = open(fullpath,"r")
		xscript2data(fh,lib_list)
		return{'FINISHED'}

lib_file = open("xscript_libraries.txt","r") # ********* REPLACE xscript_libraries.txt WITH THE FULL PATH OF THE TEXT FILE THAT CONTAINS LIBRARIES ********
defaultDir = dict([i.split("=") for i in lib_file.read().split("\n") if "=" in i]).get("directory","")
setattr(bpy.types.Scene, "file", bpy.props.StringProperty(name="file", default=""))
setattr(bpy.types.Scene, "directory", bpy.props.StringProperty(name="directory", default=defaultDir))
bpy.utils.register_class(DATA_OT_load)
bpy.utils.register_class(PANEL_PT_xscriptpanel)

lib_list = loadLibraries()
