import sys, os
import re, regex, codecs
import csv
import getopt

from bs4 import BeautifulSoup, Tag, NavigableString
import pandas as pd
from scipy import stats

opts, args = getopt.getopt(sys.argv[1:], "rpw", ["problem", "empty"])

print("""Available arguments:
-r: read data from xml, else read data from csv
-w: execute custom prints into the tex folder
-p: print the big stuff that takes a long time
--problem: print all examples which are marked with a question mark
""")

print_empty = any(opt == "--empty" for opt,arg in opts)

dir = os.getcwd()
xml_path = "gesuch.xml"
csv_path = "gesuch.csv"

df = None
count_all_matches = 0
count_rows = 0
count_words = 0

filelengths = {'Chronicle': 14418, 'Catholic Homilies': 5238, 'Letters': 23776, 'Marvels': 1737, 'Orosius': 8664, 'Prefaces': 2730}

def read():	
	auswertung = [["doc", "page", "line", "year", "match", "prefix", "gram", "person", "number", "mood", "tempus", "auxiliar", "g_kat", "lemma", "sem", "status", "rektion", "object", "obj_case", "pr_obj", "adverb", "adverb_tmp", "adverb_mod", "adjunct", "belebt", "negation", "conjunction", "clause", "context", "phenomenon", "comment", "trans", "translator", "trans_anm"]]

	debugging = False
	debug = ""
	log = ""
	logged = 0

	def new_line(lnr, content):
		tag = BeautifulSoup("z", "html.parser").new_tag('z', nr=lnr)
		tag.string = content.strip()
		
		return tag
	def open_xml(path):
		print("open", path)
		with open(path, "r", encoding="utf-8-sig") as f:
			read = f.read()
			read = re.sub("<(bf|nf)[^>]*/>", "", read)
			read = re.sub("  ", " ", read)
			soup = BeautifulSoup(read, "html.parser")
		return soup
	def split_contents(soup):
		contents = soup.contents
		splitt = []
		
		for cc in contents:
			if isinstance(cc, Tag):
				splitt.append(str(cc))
			elif isinstance(cc, NavigableString):
				cc = re.sub("[{}](?! )", "\g<0> ", cc)
				cc = re.sub("(?<! )[{{}}]", " \g<0>", cc)
				for token in cc.split():
					splitt.append(token)
			else:
				input(cc, type(cc))
		
		return splitt
	def get_soup_text(soup):
		return "".join([str(c) for c in soup.contents])
	
	def get_xml_atr(match, tag):
		if len(re.findall(" {}=\"(.*?)\"".format(tag), match.group(0))) > 1:
			print(match.group(0), tag)
			input()
		
		res = re.search(" {}=\"(.*?)\"".format(tag), match.group(0))
		return res.group(1) if res else "" 
		
	def find_beginning(line, match, line_nr):
		string = re.sub("</?match[^>]*>", "", match.string[:match.start(0)])
		trans = trans_anm = ""
		
		if "<trans" in string:
			string = re.search("(<trans(.(?!trans ))+)+", string).group(1)
			trans = get_xml_atr(re.search(".+", string), "en")
			trans_anm = get_xml_atr(re.search(".+", string), "note")
			
			string = string.rsplit("trans>", 1)[1]
			
		if "." in string or any([border_tag in match.string[:match.start(0)] for border_tag in ["<trans", "<annum"]]):
			
			this_line_text = -1
			for el in reversed(line.contents):
				if this_line_text == -1:
					if str(el)==match.group(0):
						this_line_text = ""
					continue
					
				if not any([border_tag in str(el) for border_tag in ["<trans", "<annum"]]):
					this_line_text = re.sub("<[^>]+>", "", str(el)) + this_line_text
				else:
					break
					
			string = this_line_text.rsplit(".", 1)[-1] if not this_line_text == -1 else ""
			
		else:
			previous_line = line.find_previous_sibling()
			add_from_previous=""
			
			while previous_line and not "." in previous_line.text and not any([border_tag in get_soup_text(previous_line) for border_tag in ["<trans", "<annum"]]):
				string = previous_line.text + "| " + string
				previous_line = previous_line.find_previous_sibling()
			
			if previous_line: 
				previous_string = get_soup_text(previous_line)
				previous_string = previous_string[previous_string.rfind(" ."):] if " ." in previous_string else previous_string
				if "<trans" in previous_string:
					previous_string = previous_string[previous_string.rfind("<trans"):]
					trans = get_xml_atr(re.search(".+", previous_string), "en")
					trans_anm = get_xml_atr(re.search(".+", previous_string), "note")
					
				previous_line_text = ""
				for el in reversed(previous_line.contents):
					if not any([border_tag in str(el) for border_tag in ["<trans", "<annum"]]):
						previous_line_text = re.sub("<[^>]+>", "", str(el)) + previous_line_text
					else:
						break
			
				add_from_previous = previous_line_text.rsplit(".", 1)[-1]
				if add_from_previous:
					string = add_from_previous + "| " + string

		string = re.sub("<[^>]+>", "", string)
		
		return (string + "#", trans, trans_anm)
	def find_end(line, match, line_nr):
		string = re.sub("</?match[^>]*>", "", match.string[match.end(0):])
		if "." in string or any([border_tag in match.string[match.end(0):] for border_tag in ["<trans", "<annum"]]):
			
			this_line_text = -1
			for el in line.contents:
				if this_line_text == -1:
					if str(el)==match.group(0):
						this_line_text = ""
					continue
					
				if not any([border_tag in str(el) for border_tag in ["<trans", "<annum"]]):
					this_line_text += re.sub("<[^>]+>", "", str(el))
				else:
					break
			
			string = re.split("(?<=\.)", this_line_text, maxsplit=1)[0]
		else:
			next_line = line.find_next_sibling()
			while next_line and not "." in next_line.text and not any([border_tag in get_soup_text(next_line) for border_tag in ["<trans", "<annum"]]):
				string = string + "| " + next_line.text 
				next_line = next_line.find_next_sibling()
			
			if next_line:
				next_line_text = ""
				for el in next_line.contents:
					if not any([border_tag in str(el) for border_tag in ["<trans", "<annum"]]):
						next_line_text += re.sub("<[^>]+>", "", str(el))
					else:
						break
					
				add_from_next = re.split("(?<=\.)", next_line_text, maxsplit=1)[0]
				if add_from_next:
					string = string + "| " + add_from_next
		
		string = re.sub("<[^>]+>", "", string)
		
		return "#" + string
	
	library = BeautifulSoup("<library/>", "html.parser")
	files = [os.path.join(dir, f) for f in os.listdir(dir) if f[-4:] == ".xml"]
	for f in files:
		library.library.append(open_xml(f).document)
		
	pattern = "(?|^()({match})([ {{}}])|([ {{}}])({match})([ {{}}])|([ {{}}])({match})()$)"	
	count_abs = 0
	global count_rows, count_words
	old_part = ""

	# Spalten = [["doc", "page", "line", "match", "gram", "lemma", "context", "comment"]]
	for part in library.library.find_all("document"):
		part_name = part["name"]
		year = 0
		
		filelengths[part_name] = len([token for token in part.text.split() if not token in [",", ".", "&#8228;", ";", ":", "?", "!", "–"]])
		
		for page in part.find_all("lpp"):
			page_nr = page["nr"]
			translator = page["translator"] if "translator" in page.attrs else ""
			
			for line in page.find_all("z"):
				line_nr = line["nr"]
				
				count_rows += 1
				count_words += len(re.sub("<[^>]+>|\b(\.|,|&#8228;|;|:|\?|!)\b", "", get_soup_text(line)).split())
				
				if re.search("<annum", str(line)):
					year = re.search("<annum nr=\"(\d+)\"", str(line)).group(1)
				
				for match in re.finditer('<match[^>]*>([^<]+)</match>', get_soup_text(line)):
					
						
					
					prev = find_beginning(line, match, line_nr)
					
					whole_sentence = prev[0] + match.group(1) + find_end(line, match, line_nr)
					trans = prev[1]
					trans_anm = prev[2]
					
					match_text = match.group(1)
					
					pfx_ann = get_xml_atr(match, "pfx")
					gram_ann = get_xml_atr(match, "gram")
					
					lm_ann = get_xml_atr(match, "lm")
					ann_ann = get_xml_atr(match, "ann")
					stat_ann = get_xml_atr(match, "status")
					sem_ann = get_xml_atr(match, "sem")
					reg_ann = get_xml_atr(match, "reg")
					neg_ann = get_xml_atr(match, "neg")
					clause_ann = get_xml_atr(match, "clause")
					conj_ann = get_xml_atr(match, "cnj")
					object_ann = get_xml_atr(match, "obj")
					object_case_ann = get_xml_atr(match, "obj_cs")
					pr_object_ann = get_xml_atr(match, "pr_obj")
					adverb_ann = get_xml_atr(match, "adv")
					adv_tmp_ann = get_xml_atr(match, "adv_tmp")
					adv_mod_ann = get_xml_atr(match, "adv_mod")
					adjunct_ann = get_xml_atr(match, "ad")
					adjunct_bel_ann = get_xml_atr(match, "ad_bel")
					phen_ann = get_xml_atr(match, "phen")
					
					
					person = re.search("\d", gram_ann).group(0) if re.search("\d", gram_ann) else "-"
					number = "sg" if "sg" in gram_ann else "pl" if "pl" in gram_ann else "-"
					mood = "ind" if "ind" in gram_ann else "cnj" if "cnj" in gram_ann else "imp" if "imp" in gram_ann else "prc" if "prc" in gram_ann else "inf" if "inf" in gram_ann else "-"
					tempus = "pperf" if "pperf" in gram_ann else "perf" if any([ann in gram_ann for ann in ["perf", "prc.prt."]]) else "prs" if any([ann in gram_ann for ann in ["prs", "inf", "imp"]]) else "prt" if "prt" in gram_ann else "-"
					g_kat_ann = "perf" if ("prc.prt." in gram_ann or "perf" in gram_ann) else "prt" if "prt" in gram_ann else "ger" if "prc.prs" in gram_ann else "prs" if "prs" in gram_ann else "imp" if "imp" in gram_ann else "inf" if "inf" in gram_ann else "-"
					auxiliar = "bēon" if "bpass" in gram_ann else "weorþan" if "vpass" in gram_ann else "wesan" if "perf.pass." in gram_ann else "habban" if "perf.act." in gram_ann else "-"
					
					if auxiliar == "habban" and sem_ann in ["motion", "sterben"]:
						auxiliar = "wesan"
					
					auswertung.append([part_name, page_nr, line_nr, year, match_text, pfx_ann, gram_ann, person, number, mood, tempus, auxiliar, g_kat_ann, lm_ann, sem_ann, stat_ann, reg_ann, object_ann, object_case_ann, pr_object_ann, adverb_ann, adv_tmp_ann, adv_mod_ann, adjunct_ann, adjunct_bel_ann, neg_ann, conj_ann, clause_ann, whole_sentence.replace("&", "\&").strip(), phen_ann, ann_ann, trans, translator, trans_anm])
	
	print(sum(filelengths.values()))
	
	with open(csv_path, "w", encoding="utf-8-sig", newline='') as csvfile:
		writer = csv.writer(csvfile, dialect='excel', delimiter=';')
		for row in auswertung:
			writer.writerow(row)
			
	print("saved csv")
	
	global df, count_all_matches
	df = pd.DataFrame.from_records(auswertung).fillna("")
	df = df.rename(columns=df.iloc[0]).drop(df.index[0])
	df[["line"]] = df[["line"]].apply(pd.to_numeric)
	df = df.sort_values(["doc", "page", "line"])
	count_all_matches = df.shape[0]
	
	df = df.replace("ǣ", "\\\\textaemacron{}", regex=True)
	df = df.replace("ȳ", "\\\\textymacron{}", regex=True)
	df = df.replace("&amp;", "&", regex=True)
def read_from_csv():
	global df, count_all_matches
	df = pd.read_csv(csv_path, sep=";", quotechar='"', dtype=str).fillna("")
	df[["line"]] = df[["line"]].apply(pd.to_numeric)
	df = df.sort_values(["doc", "page", "line"])
	count_all_matches = df.shape[0]
	df = df.replace("ǣ", "\\\\textaemacron{}", regex=True)
	df = df.replace("ȳ", "\\\\textymacron{}", regex=True)
	df = df.replace("&amp;", "&", regex=True)
	
def tex_path(string):
	return os.path.join("D:/Hannes/Dateien/Uni/Masterarbeit/tex/code/", "{}.tex".format(string))
def format_number(number):
	return "{:_.0f}".format(number).replace('.', ',').replace('_', '.')
def chi2(current_df, col1, col2):
	crosstab = pd.crosstab(current_df[col1], current_df[col2])
	
	stat, p, df, ex = stats.chi2_contingency(crosstab)
	cramer = stats.contingency.association(crosstab)
	
	chi, c, p = round(stat, 2), round(cramer, 2), "< 0.01" if p < 0.01 else f"≈ {round(p, 3)}"
	
	return f"\\textit{{V}} ≈ {c}, \\textit{{χ}}² ({df}, \\textit{{N}}={crosstab.sum().sum()}) ≈ {chi}, \\textit{{p}} {p}%"
def r_pb(current_df, col_num, col_cat="prefix"):
	current_df[col_cat] = current_df[col_cat].apply(lambda x: 0 if x=="0" else 1)
	current_df[col_num] = current_df[col_num].astype("int")
	
	binary_var = list(current_df[col_cat])
	continuous_var = list(current_df[col_num])
	
	r_pb, p = stats.pointbiserialr(binary_var, continuous_var)
	r_pb, p = round(r_pb, 2), "< 0.01" if p < 0.01 else f"≈ {round(p, 3)}"
	
	return f"Point-Biserial Correlation ≈ {r_pb}, \\textit{{p}} {p}%"

table_by_grammar_old_format="""
\\begin{{tabular}}{{llllll|l}}
	& inf. & prs. & prt. & prc.prs. & prc.prt. & Σ\\\\
	+\\textit{{ġe}} & {} & {} & {} & {} & {} & {} \\\\
	-\\textit{{ġe}} & {} & {} & {} & {} & {} & {} \\\\\\midrule
	Σ & {} & {} & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
table_by_grammar_format="""
\\begin{{tabular}}{{lllllll|l}}
	& inf. & prs. & imp. & prt. & prc.prs. & prc.prt. & Σ\\\\
	+\\textit{{{}}} & {} & {} & {} & {} & {} & {} & {} \\\\
	-\\textit{{{}}} & {} & {} & {} & {} & {} & {} & {} \\\\\\midrule
	Σ & {} & {} & {} & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
col_by_grammar_format="""
\\begin{{tabular}}{{lllllll|l}}
	& inf. & prs. & imp. & prt. & prc.prs. & prc.prt. & Σ\\\\
	{}\\\\\\midrule
	Σ & {} & {} & {} & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
table_grammar_by_doc_old_format="""
\\begin{{tabular}}{{llllll|l}}
	& inf. & prs. & prt. & prc.prs. & prc.prt. & Σ\\\\
	\\textit{{Chron.}} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Orosius}} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Marvels}} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Cath. Homil.}} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Letters}} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Prefaces}} & {} & {} & {} & {} & {} & {} \\\\\\midrule
	Σ & {} & {} & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
table_grammar_by_doc_format="""
\\begin{{tabular}}{{lllllll|l}}
	& inf. & prs. & imp. & prt. & prc.prs. & prc.prt. & Σ\\\\
	\\textit{{Chron.}} & {} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Orosius}} & {} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Marvels}} & {} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Cath. Homil.}} & {} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Letters}} & {} & {} & {} & {} & {} & {} & {} \\\\
	\\textit{{Prefaces}} & {} & {} & {} & {} & {} & {} & {} \\\\\\midrule
	Σ & {} & {} & {} & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
table_by_doc_format="""
\\begin{{tabular}}{{lll|ll}}
	& +\\textit{{ġe}} & -\\textit{{ġe}} & Σ & pro 100k\\\\
	\\textit{{Chron.}} & {} & {} & {} & {} \\\\
	\\textit{{Orosius}} & {} & {} & {} & {} \\\\
	\\textit{{Marvels}} & {} & {} & {} & {} \\\\
	\\textit{{Cath. Homil.}} & {} & {} & {} & {} \\\\
	\\textit{{Letters}} & {} & {} & {} & {} \\\\
	\\textit{{Prefaces}} & {} & {} & {} & {} \\\\\\midrule
	Σ & {} & {} & {} & {} \\\\
\\end{{tabular}}

"""
def write_table_by_grammar(current_df, prefix="ge"):
	values = []
	
	prefix_ = "ġe" if prefix == "ge" else prefix
	
	values.append(prefix_)
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["prefix"].str.contains(prefix))].shape[0] or "")
	
	values.append(prefix_)
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix)) & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[~(current_df["prefix"].str.contains(prefix))].shape[0] or "")
	
	values.append(current_df[(current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df.shape[0] or "")
	
	return table_by_grammar_format.format(*values)
def write_col_by_grammar(current_df, col):
	values = []
	for value, row in current_df.groupby(col):
		value = "ġe-" if value == "ge" else value + "-"
		values_ = [f"\\textit{{{value}}}"]
		values_.append(row[(row["g_kat"]=="inf")].shape[0] or "")
		values_.append(row[(row["g_kat"]=="prs")].shape[0] or "")
		values_.append(row[(row["g_kat"]=="imp")].shape[0] or "")
		values_.append(row[(row["g_kat"]=="prt")].shape[0] or "")
		values_.append(row[(row["g_kat"]=="ger")].shape[0] or "")
		values_.append(row[(row["g_kat"]=="perf")].shape[0] or "")
		values_.append(row.shape[0] or "")
		
		values.append(" & ".join([str(vl) for vl in values_]))
	
	values = ["\\\\\n\t".join(values)]
	
	values.append(current_df[(current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df.shape[0] or "")
	
	return col_by_grammar_format.format(*values)

def write_table_grammar_by_doc(current_df):
	values = []
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle")].shape[0] or "")
	
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius")].shape[0] or "")
	
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels")].shape[0] or "")
	
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies")].shape[0] or "")
	
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters")].shape[0] or "")
	
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces")].shape[0] or "")
	
	values.append(current_df[(current_df["g_kat"]=="inf")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prs")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="imp")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="prt")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="ger")].shape[0] or "")
	values.append(current_df[(current_df["g_kat"]=="perf")].shape[0] or "")
	values.append(current_df.shape[0] or "")
	
	return table_grammar_by_doc_format.format(*values)
def write_table_by_doc(current_df):
	values = []
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Chronicle")].shape[0]*100000//filelengths["Chronicle"] or "")
	
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Orosius")].shape[0]*100000//filelengths["Orosius"] or "")
	
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Marvels")].shape[0]*100000//filelengths["Marvels"] or "")
	
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Catholic Homilies")].shape[0]*100000//filelengths["Catholic Homilies"] or "")
	
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Letters")].shape[0]*100000//filelengths["Letters"] or "")
	
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces") & (current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces")].shape[0] or "")
	values.append(current_df[(current_df["doc"]=="Prefaces")].shape[0]*100000//filelengths["Prefaces"] or "")
	
	values.append(current_df[(current_df["prefix"]=="ge")].shape[0] or "")
	values.append(current_df[(current_df["prefix"]=="0")].shape[0] or "")
	values.append(current_df.shape[0] or "")
	values.append(current_df.shape[0]*100000//sum(filelengths.values()) or "")
	
	return table_by_doc_format.format(*values)
def write_table_by_lemma(current_df, non_zero=[]):
	table_by_lemma_format="""
\\begin{{tabular}}{{lll|l}}
	& +\\textit{{ġe}} & -\\textit{{ġe}} & Σ\\\\
	{}\\midrule Σ & {} & {} & {} \\\\
\\end{{tabular}}

"""
	table_by_lemma_line_format="\t{} & {} & {} & {}\\\\\n"
	
	table_content = ""
						
	for lemma,dff in current_df.groupby("lemma"):
		
		values = []
		values.append(lemma) #Lemma
		
		values.append(dff[dff["prefix"]=="ge"].shape[0]) 
		values.append(dff[dff["prefix"]=="0"].shape[0]) 
		values.append(dff.shape[0])

		table_content += table_by_lemma_line_format.format(*values)
	
	return table_by_lemma_format.format(table_content, current_df[current_df["prefix"]=="ge"].shape[0], current_df[current_df["prefix"]=="0"].shape[0], current_df.shape[0])

table_by_col_format="""
\\begin{{tabular}}{{lll|ll}}
	& +\\textit{{{pp}}} & -\\textit{{{pp}}} & Σ\\\\
	{cc}
\\end{{tabular}}

"""
table_by_col_row_format="\\textit{{{}}} & {} & {} & {}\\\\"
def write_table_by_col(current_df, column_name, non_zero={}, zero={}, sort=None, prefix="ge"):
	if column_name in current_df:
		table = []
		sum = ["Σ", 0, 0, 0]
		
		for col, dff in current_df.groupby(column_name):
			if prefix in non_zero and dff[dff["prefix"]==prefix].shape[0] == 0:
				continue
			if "0" in non_zero and dff[dff["prefix"]=="0"].shape[0] == 0:
				continue
		
			table.append([col, dff[dff["prefix"]==prefix].shape[0], dff[dff["prefix"]=="0"].shape[0], dff.shape[0]])
			sum = ["Σ", sum[1] + dff[dff["prefix"]==prefix].shape[0], sum[2] + dff[dff["prefix"]=="0"].shape[0], sum[3] + dff.shape[0]]
			
		
		if table:
			if sort:
				if sort == "percentage":
					table = sorted(table, key=lambda x: x[1]/x[2] if x[2] else 1, reverse=True)
				if sort == "total":
					table = sorted(table, key=lambda x: (x[3], x[2]), reverse=True)
				if sort == "reverse":
					table = sorted(table, reverse=True)
			
			table_content = "".join([table_by_col_row_format.format(*el) for el in table]) + "\\hline\n\t" + table_by_col_row_format.format(*sum)
			
			table_content
			
			prefix = "ġe" if prefix == "ge" else prefix
			return table_by_col_format.format(pp=prefix,cc=table_content)
	else:
		return column_name + " not in dataframe"
	
	
def write_table(current_df):
	return write_table_by_grammar(current_df) + write_table_grammar_by_doc(current_df) + write_table_by_doc(current_df)
	
beispiel_format = """
\\begin{{xltabular}}{{\\textwidth}}{{lL}}
	{src} & \\textit{{{ctx}}} \\\\\\nopagebreak
	& ‚{trs}‘ {nt}\\\\
\\end{{xltabular}}

"""
alt_beispiel_format = """
\\textit{{{ctx}}} \\hspace*{{\\fill}}\\allowbreak\\hspace*{{\\fill}} \\mbox{{({src})}} \\\\
‚{trs}‘ {nt}

"""
def write_example(current_df, alt=True, verbose=False, condense=False, include={}, dont_include={}, cross={}, howmany=0, return_number=False):
	def include_key(row, include, key):
		if key in row and key in include.keys():
			return all([k in [kk for kk in set(row[key])] for k in include[key]])
		else:
			input(key + " is not a valid column")
			return True
	def dont_include_key(row, dont_include, key):
		if key in row and key in dont_include.keys():
			return any([k in [kk for kk in set(row[key])] for k in dont_include[key]])
		else:
			input(key + " is not a valid column")
			return False
	
	current_df = current_df.copy() #turns off annoying warning https://stackoverflow.com/questions/49728421/pandas-dataframe-settingwithcopywarning-a-value-is-trying-to-be-set-on-a-copy
	if condense: 
		current_df.loc[:,"raw"] = current_df.loc[:,"context"].apply(lambda x: re.sub("#", "", x))
		
		generator = current_df.groupby("raw", sort=False)
	else:
		generator = current_df.iterrows()
	
	beispiel_tex = ""
	count = 0
	for index,row in generator:
		verbose_ = [key for key in verbose] if verbose else []
		
		if condense:
			skip = False
			for inc in include:
				if not include_key(row, include, inc):
					skip = True
			for dinc in dont_include:
				if dont_include_key(row, dont_include, dinc):
					skip = True
			
			if skip:
				continue
			
			for label1 in cross.keys():
				label2 = cross[label1]
				lefts = set(row[label1])
				rights = set(row[label2])
				
				intersect = lefts.intersection(rights)
				
				row = row[(row[label1].isin(intersect)) | (row[label2].isin(intersect))]
				
			if row.shape[0] == 0:
				continue
			
			
			contexts = list(set(row["context"]))
			
			while len(contexts) > 1:
				ii = 0
				while ii < len(contexts[0]):
					bukvy = [c[ii] for c in contexts]
					
					if len(set(bukvy)) > 1:
						for yy in range(len(contexts)):
							if bukvy[yy] != "#":
								contexts[yy] = contexts[yy][:ii] + "#" + contexts[yy][ii:]
								
					ii+=1
				contexts = list(set(contexts))
			context = contexts[0]
								
			doc = [d for d in set(row["doc"])]
			page = [p for p in list(row["page"].unique())] #set vertauscht die Reihenfolge
			line = [str(l) for l in list(row["line"].unique())]
			lemma = [lm for lm in list(row["lemma"].unique())]
			gram = [g for g in list(row["gram"].unique())]
			
			doc = ", ".join(doc)
			page = ", ".join(page)
			#line = ", ".join(line)
			line = line[0] + "–" + line[-1] if len(line) > 1 else line[0]
			lemma = ", ".join(lemma)
			gram = ", ".join(gram)
			
			year = str(set(row["year"]).pop())
			trans = set(row["trans"]).pop()
			trans_anm = set(row["trans_anm"]).pop()
			translator = set(row["translator"]).pop()
			translator = translator + "\mancite" if translator else ""
		else:	
			context = row["context"]
			
			doc = row["doc"]
			page = row["page"]
			line = str(row["line"])
			lemma = row["lemma"]
			gram = row["gram"]
			
			year = str(row["year"])
			trans = row["trans"]
			trans_anm = row["trans_anm"]
			translator = row["translator"] + "\mancite" if row["translator"] else ""
		
		count += 1
		
		if howmany and count > howmany:
			break
		
		context = re.sub("#(.+?)#", "\\\\textbf{\g<1>}", context)
		context = re.sub(" (,|\.|;|:|\?|!|․)", "\g<1>", context)
		context = re.sub("․", ".", context)
		
		page = page.replace("(1)", "I").replace("(2)", "II")
		
		if doc == "Orosius":
			doc = "Or"
			
			translator = translator + ": " + page
			page = ""
			
		elif doc == "Chronicle":
			doc = "Chron."
			page = ""
			
			translator = (translator + ": Jahr " + year) if year else translator
			
		elif doc == "Catholic Homilies":
			doc = "Cath. Hom."
			doc = "CH"
		elif doc == "Letters":
			doc, page = page, ""
			doc = doc.replace("To ", "")
		elif doc == "Prefaces":
			doc = "Prf."
			page = page.replace("To ", "to ")
			
			if "Catholic Homilies" in page:
				page = page.replace("Catholic Homilies", "CH")
				
		elif doc == "Marvels":
			page = ""
			
		source = doc + " " + page + " " + line
		
		if r"\eUe" in trans_anm:
			translator = trans_anm
			trans_anm = ""
		elif trans_anm:
			trans_anm = "; " + trans_anm
		note = "({})".format(translator + trans_anm)
		
		comment = row["comment"]
		if "?" in comment and not "comment" in verbose_:
			verbose_ += ["comment"]
		
		if verbose_ and any([key in row for key in verbose_]):
			note += "\\newline "
			
			for key in verbose_:
				if key in row:
					key_ = ", ".join(row[key].unique()) if condense else row[key]
					if key == "lemma":
						note += "\\vspace{{.5em}}\\textbf{{\\fontspec{{Palemonas}}{}}}".format(lemma) 
					elif key == "year":
						note += "Jahr " + str(key_)
					else:
						note += "\\textbf{{{}}}".format(key_)
					note += ", "
				
			note = note[:-2] + "\\vspace{{.5em}}"
			
			note =""
		
		bsp = alt_beispiel_format.format(src=source, ctx=context, trs=trans, nt=note) if alt else beispiel_format.format(src=source, ctx=context, trs=trans, nt=note)
		
		beispiel_tex += bsp
	
	if return_number:
		return format_number(count)
	return beispiel_tex

def write_tex(fName, text):
	print(fName)
	text = "" if print_empty else text
	text = text.replace("{label}", f"\\label{{tex:{fName}}}")
	with open(tex_path(fName), "w", encoding="utf-8") as file:
		file.write(text.strip().replace(r"""\end{xltabular}\n\n\n\begin{xltabular}{\textwidth}{lL}""", "") + "%")

def lemma_pivot(current_df, index="lemma", cols="prefix", prefix="ge", incl_pref={}, incl_zero={}, no_pref={}, no_zero={}, howmany=0, sort=None, total=True, multicols=3):
	current_df = current_df.copy()
	
	if current_df[current_df["lemma"]==""].shape[0] > 0:
		input(current_df[current_df["lemma"]==""][["doc", "page", "line", "match"]])
		
	for ii,dff in current_df.groupby(index):
		skip = False
		
		# kann ich hier auch eine synonyme == False Abfrage machen, oder kann das dazu führen, dass im Zweifel else nicht ausgeführt wird?	
		
		if incl_pref == True:
			if dff[dff["prefix"]==prefix].shape[0] == 0:
				skip = True
		else:
			for key in incl_pref:
				for value in incl_pref[key]:
					if dff[(dff[cols]==prefix) & (dff[key]==value)].shape[0] == 0:
						skip = "#1"
					
		if incl_zero == True:
			if dff[dff["prefix"]=="0"].shape[0] == 0:
				skip = True
		else:
			for key in incl_zero:
				for value in incl_zero[key]:
					if dff[(dff[cols]=="0") & (dff[key]==value)].shape[0] == 0:
						skip = "#2"
		
		if skip:
			current_df.drop(current_df[(current_df[index]==ii)].index, inplace=True)
			continue
		
		if no_pref == True:
			if not dff[dff["prefix"]==prefix].shape[0] == 0:
				skip = True
		else:
			for key in no_pref:
				for value in no_pref[key]:
					if not dff[(dff[cols]==prefix) & (dff[key]==value)].shape[0] == 0:
						skip = "#3"
		
		if no_zero == True:
			if not dff[dff["prefix"]=="0"].shape[0] == 0:
				skip = True
		else:	
			for key in no_zero:
				for value in no_zero[key]:
					if not dff[(dff[cols]=="0") & (dff[key]==value)].shape[0] == 0:
						skip = "#4"
	
		
		if skip:
			current_df.drop(current_df[(current_df[index]==ii)].index, inplace=True)
	
	pivot_df = current_df.loc[:,[index, cols]].replace(".+ge", "ge", regex=True).pivot_table(columns=[cols], index=[index], values=cols, aggfunc='size', fill_value=0)
	
	pivot_df['Total'] = pivot_df.sum(axis=1)
	if sort:
		if sort == "total":	
			pivot_df = pivot_df.sort_values(["Total", prefix], ascending=False)
		if sort == "percentage":
			pivot_df['Total'] = pivot_df["ge"].div(pivot_df["Total"], fill_value=0)
			pivot_df = pivot_df.sort_values(["Total"], ascending=True)
	
	if not total:
		pivot_df = pivot_df.drop(["Total"], axis=1)
	
	if not pivot_df.shape[0]:
		print("Warning: Resulting Dataframe is empty")
	
	if howmany:
		pivot_df = pivot_df.iloc[0:howmany]
	
	prefix_ = "ġe" if prefix == "ge" else prefix
	
	longest_lemma = max(pivot_df.index, key=lambda x: len(re.sub("\\\\.+?\{\}", "X", x)))
	pivot_df.loc['\\textup{\\textbf{Σ}}'] = pivot_df.sum()
	head = pivot_df.columns.str.replace(prefix, "+" + prefix_).str.replace("0", "-" + prefix_).str.replace("Total", "Σ")
	
	pivot_df = pivot_df.to_string().split('\n')
	body = pivot_df[2:]
	
	head_str = f"\\settowidth\\mylength{{{longest_lemma}0}}\\hspace{{\\mylength}} \= " + "\\phantom{{0}} \= ".join(["\\bfseries " + hh for hh in head]) 
	
	pivot_df = ["\\itshape " + " \> ".join(ele.split()) for ele in body]
	
	if multicols:
		return head_str + "\n\\end{tabbing}\\end{multicols}\n\n\\begin{multicols}{3}\\begin{tabbing}\n" + head_str + "\\kill\n" + " \\\\\n".join(pivot_df)
	else:
		return " \\\\\n".join([head_str] + pivot_df)


def write():
	global df
	
	print(filelengths)
	
	cnj_str = "(?:(?<=3.sg.)|(?<=pl.))cnj.(?!p?perf)"
	
	df = df[~df["status"].str.match("^(hidden|nomen)$")]
	
	write_tex("overview", write_table(df))
	
	#Sachen mit festen Präfixen:
	seon_df = df[(df["lemma"]=="sēon")]
	write_tex("seon_by_gram", write_table_by_grammar(seon_df))
	write_tex("seon_bsp_indFr_Or", write_example(seon_df[(seon_df["doc"]=="Orosius") & (seon_df["clause"]=="indFrag")]))
	write_tex("seon_bsp_þa_ga", write_example(seon_df[(seon_df["conjunction"]=="þā") & (seon_df["prefix"]=="ge")]))
	
	write_tex("ġebyrian_bsp_swā", write_example(df[(df["lemma"]=="ġebyrian") & (df["conjunction"]=="swā")]))
	write_tex("don_ein_bsp_motion", write_example(df[(df["lemma"]=="dōn") & (df["sem"]=="motion")].iloc[0:1,:]))
	
	gewitan_df = df[df["lemma"]=="ġewītan"]
	write_tex("gewitan_by_gram", write_table_by_grammar(gewitan_df))
	write_tex("gewitan_ein_bsp", write_example(gewitan_df.iloc[:1]))
	write_tex("gewitan_ein_bsp_sterben", write_example(gewitan_df[(gewitan_df["line"]==853)].iloc[:1]))
	
	#gemunan (fest!)
	munan_df = df[df["lemma"].str.contains("munan")]
	write_tex("munan_by_gram", write_table_by_grammar(munan_df))
	write_tex("munan_bsp", write_example(munan_df, True))
	write_tex("munan_bsp_prc", write_example(munan_df[munan_df["gram"].str.contains("prc.prs.")], True))
	write_tex("munan_bsp_inf", write_example(munan_df[~munan_df["gram"].str.contains("prc.prs.")], True))
	#fyllan
	fyllan_df = df[df["lemma"]=="fyllan"]
	write_tex("fyllan_by_gram", write_table_by_grammar(fyllan_df))
	
	#q-hapax
	faktitiv_df = df[(df["status"]=="q-hapax") & (df["sem"]=="faktitiv")]
	write_tex("faktitiv_ga_lemmata", write_col_by_grammar(faktitiv_df, "lemma"))
	write_tex("faktitiv_bsp_inf", write_example(faktitiv_df[(faktitiv_df["g_kat"]=="inf") & (faktitiv_df["clause"].isin(["HS", "dassSatz", "final"]))]))
	write_tex("faktitiv_bsp_prs", write_example(faktitiv_df[(faktitiv_df["g_kat"]=="prs") & (faktitiv_df["clause"].isin(["HS", "dassSatz", "relSatz"]))]))
	write_tex("faktitiv_bsp_prt", write_example(faktitiv_df[(faktitiv_df["g_kat"]=="prt") & (faktitiv_df["clause"].isin(["HS", "final"]))]))
	
	faktitiv_0_df = df[(df["sem"]=="faktitiv") & (df["prefix"]=="0")]
	write_tex("faktitiv_0_by_lemma", write_col_by_grammar(faktitiv_0_df, "lemma"))
	write_tex("faktitiv_bsp_inf_0", write_example(faktitiv_0_df[(faktitiv_0_df["g_kat"]=="inf")]))
	write_tex("faktitiv_bsp_prs_0", write_example(faktitiv_0_df[(faktitiv_0_df["g_kat"]=="prs")]))
	write_tex("faktitiv_bsp_prt_0", write_example(faktitiv_0_df[(faktitiv_0_df["g_kat"]=="prt")]))
	
	#Sachen mit der condense- und (dont_)include-Funktion, bei der Textstellen auf der Basis von Lemma-übergreifenden Faktoren gesucht werden
	def combination_search():
		#Krieg
		kriegsverben = ["ġeflīeman", "ofslēan", "slēan", "winnan", "hergian", "brecan", "mētan", "þingian", "bringan", "niman", "āgan", "sēon"]
		fight_df = df[(df["doc"]=="Chronicle") & (((((df["lemma"]=="feohtan") & (df["clause"]=="HS") & (df["obj_case"]=="")) | (df["sem"].isin(["motion", "sterben"])) | (df["adjunct"].str.contains("siġe|friþ|ġeweald"))) & (df["g_kat"]=="prt")) | ((df["lemma"].isin(kriegsverben)) & (df["g_kat"].isin(["prt", "perf"]))) | (df["lemma"].isin(["cweþan", "nemnan", "hātan"])))]
		
		write_tex("just_fight_0", write_example(fight_df[fight_df["doc"]=="Chronicle"].sort_values("line"), condense=True, include={"lemma" : ["feohtan"]}, dont_include={"prefix" : ["ge", "of"], "lemma" : ["nemnan", "cweþan", "hātan"] + kriegsverben, "sem" : ["motion", "sterben"]}))
		write_tex("just_fight_0_count", write_example(fight_df[fight_df["doc"]=="Chronicle"], condense=True, include={"lemma" : ["feohtan"]}, dont_include={"prefix" : ["ge", "of"], "lemma" : ["nemnan", "cweþan", "hātan"] + kriegsverben, "sem" : ["motion", "sterben"]}, return_number=True))
		write_tex("just_fight_ga", write_example(fight_df[fight_df["doc"]=="Chronicle"].sort_values("line"), condense=True, include={"lemma" : ["feohtan"]}, dont_include={"prefix" : ["0"], "lemma" : ["cweþan", "nemnan", "hātan"] + kriegsverben, "sem" : ["motion", "sterben"]}))
		write_tex("just_fight_ga_count", write_example(fight_df[fight_df["doc"]=="Chronicle"], condense=True, include={"lemma" : ["feohtan"]}, dont_include={"prefix" : ["0"], "lemma" : ["cweþan", "nemnan", "hātan"] + kriegsverben, "sem" : ["motion", "sterben"]}, return_number=True))
		
		write_tex("fight_in", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & ~(fight_df["adverb"]=="in+d"))], condense=True, include={"lemma" : ["feohtan"]}))
		write_tex("fight_in_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (~(fight_df["adverb"]=="in+d") | (fight_df["prefix"]=="0")))], condense=True, include={"lemma" : ["feohtan"]}))
		write_tex("fight_in_0", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (~(fight_df["adverb"]=="in+d") | (fight_df["prefix"]=="ge")))], condense=True, include={"lemma" : ["feohtan"]}))
		write_tex("fight_in_count", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & ~(fight_df["adverb"]=="in+d"))], condense=True, include={"lemma" : ["feohtan"]}, return_number=True))
		
		write_tex("fight_geflieman_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ġeflīeman")], condense=True, include={"lemma" : ["feohtan", "ġeflīeman"]}))
		write_tex("fight_ein_bsp_geflieman_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) & (fight_df["line"]>233) | (fight_df["lemma"]=="ġeflīeman")], condense=True, howmany=1, include={"lemma" : ["feohtan", "ġeflīeman"]}))
		write_tex("fight_zwei_bsp_geflieman_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ġeflīeman")], condense=True, howmany=2, include={"lemma" : ["feohtan", "ġeflīeman"]}))
		write_tex("fight_geflieman_ga_count", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ġeflīeman")], condense=True, include={"lemma" : ["feohtan", "ġeflīeman"]}, return_number=True))
		write_tex("fight_geflieman_0", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ġeflīeman")], condense=True, include={"lemma" : ["feohtan", "ġeflīeman"]}))
		write_tex("fight_zwei_bsp_geflieman_0", write_example(fight_df[(((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ġeflīeman")) & (fight_df["line"]<800)], condense=True, include={"lemma" : ["feohtan", "ġeflīeman"]}))
		write_tex("fight_geflieman_0_count", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge")) | (fight_df["lemma"]=="ġeflīeman")], condense=True, include={"lemma" : ["feohtan", "ġeflīeman"]}, return_number=True))

		
		write_tex("fight_him_wiþ_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0"))], condense=True, include={"lemma" : ["feohtan"], "adjunct" : ["him"]}))
		write_tex("fight_him_wiþ_0", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge"))], condense=True, include={"lemma" : ["feohtan"], "adjunct" : ["him"]}))
		
		
		write_tex("fight_sige_ga", write_example(fight_df[(fight_df["prefix"]=="ge")], condense=True, include={"lemma" : ["feohtan", "niman"]}))
		write_tex("fight_sige_0", write_example(fight_df[(fight_df["prefix"]=="0")], condense=True, include={"lemma" : ["feohtan", "niman"]}))
		write_tex("fight_sige_ga_0", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge")) | ((fight_df["lemma"]=="niman") & (fight_df["prefix"]=="0"))], condense=True, include={"lemma" : ["feohtan", "niman"]}))
		write_tex("fight_sige_0_ga", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | ((fight_df["lemma"]=="niman") & (fight_df["prefix"]=="ga"))], condense=True, include={"lemma" : ["feohtan", "niman"]}))
		
		write_tex("fight_hergian_ga", write_example(fight_df[(fight_df["prefix"]=="ge")], condense=True, include={"lemma" : ["feohtan", "hergian"]}))
		write_tex("fight_hergian_0", write_example(fight_df[(fight_df["prefix"]=="0")], condense=True, include={"lemma" : ["feohtan", "hergian"]}))
		write_tex("fight_hergian_ga_0", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge")) | ((fight_df["lemma"]=="hergian") & (fight_df["prefix"]=="0"))], condense=True, include={"lemma" : ["feohtan", "hergian"]}))
		write_tex("fight_hergian_0_ga", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | ((fight_df["lemma"]=="hergian") & (fight_df["prefix"]=="ga"))], condense=True, include={"lemma" : ["feohtan", "hergian"]}))
		
		write_tex("fight_ofslean_ga", write_example(fight_df[(fight_df["prefix"]=="ge") | (fight_df["prefix"]=="of")], condense=True, include={"lemma" : ["feohtan", "ofslēan"]}))
		write_tex("fight_zwei_bsp_ofslean_ga", write_example(fight_df[(fight_df["prefix"]=="ge") | (fight_df["prefix"]=="of")], condense=True, howmany=2, include={"lemma" : ["feohtan", "ofslēan"]}))
		write_tex("fight_ofslean_ga_count", write_example(fight_df[(fight_df["prefix"]=="ge") | (fight_df["prefix"]=="of")], condense=True, include={"lemma" : ["feohtan", "ofslēan"]}, return_number=True))
		write_tex("fight_ofslean_0_ga", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ofslēan")], condense=True, include={"lemma" : ["feohtan", "ofslēan"]}))
		write_tex("fight_zwei_bsp_ofslean_0_ga", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ofslēan")], condense=True, howmany=2, include={"lemma" : ["feohtan", "ofslēan"]}))
		write_tex("fight_ofslean_0_ga_count", write_example(fight_df[((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="ofslēan")], condense=True, include={"lemma" : ["feohtan", "ofslēan"]}, return_number=True))
		write_tex("fight_slean_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="slēan")], condense=True, include={"lemma" : ["feohtan", "slēan"]}))
		write_tex("fight_zwei_bsp_slean_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0")) | (fight_df["lemma"]=="slēan")], condense=True, howmany=2, include={"lemma" : ["feohtan", "slēan"]}))
		write_tex("fight_slean_0", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge")) | (fight_df["lemma"]=="slēan")], condense=True, include={"lemma" : ["feohtan", "slēan"]}))
		
		write_tex("fight_motion_ga", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="0"))], condense=True, include={"lemma" : ["feohtan"], "sem" : ["motion"]}))
		write_tex("fight_motion_0", write_example(fight_df[~((fight_df["lemma"]=="feohtan") & (fight_df["prefix"]=="ge"))], condense=True, include={"lemma" : ["feohtan"], "sem" : ["motion"]}))
		
		write_tex("fight_ge_0", write_example(fight_df[fight_df["lemma"]=="feohtan"], condense=True, include={"prefix" : ["0", "ge"]}))
		
		schreiben_df = df[(df["lemma"].str.contains("wrītan")) | (df["status"]=="aux")]
		write_tex("writan_awritan_bsp", write_example(schreiben_df, condense=True, include={"lemma" : ["wrītan", "āwrītan"]}))
		write_tex("writan_bsp_neg", write_example(schreiben_df[(schreiben_df["g_kat"]=="prt") & ~(schreiben_df["negation"]=="0") & ~(schreiben_df["status"]=="aux")], condense=True))
		write_tex("writan_ein_bsp_neg", write_example(schreiben_df[(schreiben_df["g_kat"]=="prt") & ~(schreiben_df["negation"]=="0") & ~(schreiben_df["status"]=="aux") & (schreiben_df["line"]==710)], condense=True))
		write_tex("awritan_ein_bsp_perf", write_example(schreiben_df[(schreiben_df["lemma"]=="āwrītan") & (schreiben_df["g_kat"]=="perf")].iloc[:1]))
		write_tex("awritan_by_gram", write_col_by_grammar(schreiben_df[(schreiben_df["lemma"].str.contains("wrītan"))], "prefix"))
		
		#Modalverben
		cross = {"rektion" : "lemma"}
		
		modverb_df = df[((df["gram"]=="inf.") & ~(df["rektion"].isin(["0", "ūtan", "hātan", "dōn", "þenċan", "hīeran"])) & ~(df["status"].isin(["fest", "q-hapax", "sem"]))) | ((df["status"]=="modalverb"))]
		write_tex("modalverben_lose", write_example(modverb_df, condense=True, include={"gram" : ["inf."]}, dont_include={"status" : ["modalverb"]}))
		
		modverb_willan_df = modverb_df[~((modverb_df["status"]=="modalverb") & (~(modverb_df["lemma"]=="willan")))]
		write_tex("modalverben_wolde_ga", write_example(modverb_willan_df[~((modverb_willan_df["status"]=="modalverb") & ~(modverb_willan_df["g_kat"]=="prt")) & ~(modverb_willan_df["prefix"]=="0")], condense=True, include={"gram" : ["inf."], "status" : ["modalverb"]}, cross=cross))
		write_tex("modalverben_wolde_0", write_example(modverb_willan_df[~((modverb_willan_df["status"]=="modalverb") & ~(modverb_willan_df["g_kat"]=="prt")) & ~(modverb_willan_df["prefix"]=="ge")], condense=True, include={"gram" : ["inf."], "status" : ["modalverb"]}, cross=cross))
		write_tex("modalverben_wille_ga", write_example(modverb_willan_df[~((modverb_willan_df["status"]=="modalverb") & ~(modverb_willan_df["g_kat"]=="prs")) & ~(modverb_willan_df["prefix"]=="0")], condense=True, include={"gram" : ["inf."], "status" : ["modalverb"]}, cross=cross))
		write_tex("modalverben_wille_0", write_example(modverb_willan_df[~((modverb_willan_df["status"]=="modalverb") & ~(modverb_willan_df["g_kat"]=="prs")) & ~(modverb_willan_df["prefix"]=="ge")], condense=True, include={"gram" : ["inf."], "status" : ["modalverb"]}, cross=cross))
		
		#zu tun denken
		think_df = df[((df["conjunction"].isin(["þenċan", "þynċan"])) & ~(df["status"].isin(["fest", "q-hapax", "sem"]))) | ((df["lemma"].isin(["þenċan", "þynċan"]))) | ((df["status"]=="modalverb"))]
		write_tex("think_to_do", write_example(think_df, include={"g_kat" : ["prt", "inf"]}))
		
		#geben und nehmen
		niman_sellan_df = df[(df["lemma"].isin(["niman", "sellan"]))]
		write_tex("niman_sellan", write_example(niman_sellan_df, condense=True, include={"lemma" : ["niman", "sellan"]}))
		
		#bauen
		bauen_df  = df[(df["lemma"].isin(["timbran", "wyrċan"]))]
		write_tex("wyrcan_timbran", write_example(bauen_df, condense=True, include={"lemma" : ["timbran", "wyrċan"]}))
		
		write_tex("imperative", write_example(df[(df["lemma"].isin(["settan", "gladian", "offrian", "þenċan"])) & (df["g_kat"].isin(["imp", "prs"])) & (df["line"]<26)], condense=True))
		
	combination_search()
	
	#Perfektgeschichten
	def write_perfekt():
		perf_df = df[(df["g_kat"]=="perf") & (df["prefix"].isin(["ge", "0"]))]
		write_tex("perfekt_lemmata", lemma_pivot(perf_df[~(perf_df["status"].isin(["q-hapax", "hapax", "fest"]))], incl_pref=True))
		write_tex("perfekt_flexible", write_table_by_col(perf_df[~(perf_df["status"].isin(["q-hapax", "hapax", "fest"]))], "lemma", non_zero=["0"]))
		
		perfekt_doc_df = perf_df[perf_df["lemma"].isin(perf_df[perf_df["prefix"]=="0"]["lemma"].unique())]
		write_tex("perfekt_by_doc", write_table_by_doc(perfekt_doc_df))
		perfekt_doc_df.loc[:,"doc"] = perfekt_doc_df.loc[:,"doc"].apply(lambda x: re.sub("Letters|Catholic Homilies|Prefaces", "Ælfric", x))
		write_tex("chi2_perfekt_by_doc", chi2(perfekt_doc_df, "doc", "prefix"))
		
		write_tex("lemma_gram_ger_only", lemma_pivot(df[~(df["status"]=="prc-only")], incl_zero={"g_kat" : ["ger"]}, no_pref={"g_kat" : ["ger"]}, no_zero={"mood" : ["ind", "cnj"]}, multicols=False))
		
		#Anzahl an Präfixen nach Lemma wenn mindestens ein unpräfigiertes Partizip vorhanden ist
		#lm=cennan (Marvels)
		write_tex("cennan_perf_count", write_table_by_doc(perf_df[perf_df["lemma"]=="cennan"]))
		write_tex("cennan_perf_ein_bsp", write_example(perf_df[perf_df["lemma"]=="cennan"].iloc[2:3,:]))
		write_tex("cennan_perf_bsp", write_example(perf_df[perf_df["lemma"]=="cennan"]))
		#lm punktuelle
		write_tex("bringan_perf_by_doc", write_table_by_doc(perf_df[perf_df["lemma"]=="bringan"]))
		write_tex("bringan_perf_bsp", write_example(perf_df[perf_df["lemma"]=="bringan"]))
		write_tex("bringan_perf_bsp_0", write_example(perf_df[(perf_df["lemma"]=="bringan") & (perf_df["prefix"]=="0")]))
		write_tex("bringan_perf_bsp_ga", write_example(perf_df[(perf_df["lemma"]=="bringan") & (perf_df["prefix"]=="ge")]))
		write_tex("bringan_perf_ein_bsp_ga", write_example(perf_df[(perf_df["lemma"]=="bringan") & (perf_df["prefix"]=="ge")].iloc[:1]))
		write_tex("findan_perf_bsp_0", write_example(perf_df[(perf_df["lemma"]=="findan") & (perf_df["prefix"]=="0")]))
		write_tex("findan_perf_bsp_ga", write_example(perf_df[(perf_df["lemma"]=="findan") & (perf_df["prefix"]=="ge")]))
		write_tex("cuman_perf_by_doc", write_table_by_doc(perf_df[perf_df["lemma"]=="cuman"]))
		write_tex("cuman_perf_bsp", write_example(perf_df[perf_df["lemma"]=="cuman"], True))
		write_tex("cuman_perf_bsp_ga", write_example(perf_df[(perf_df["lemma"]=="cuman") & (perf_df["prefix"]=="ge")], True))
		write_tex("cuman_perf_bsp_0", write_example(perf_df[(perf_df["lemma"]=="cuman") & (perf_df["prefix"]=="0")], True, condense=True))
		#lm=nemnan
		write_tex("nemnan_perf_count", write_table_by_doc(perf_df[perf_df["lemma"]=="nemnan"]))
		write_tex("nemnan_perf_bsp", write_example(perf_df[perf_df["lemma"]=="nemnan"].sort_values(["prefix"]), condense=True))
		write_tex("nemnan_perf_bsp_0_Chr", write_example(perf_df[(perf_df["lemma"]=="nemnan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["prefix"]=="0")]))
		write_tex("nemnan_perf_bsp_ga_Chr", write_example(perf_df[(perf_df["lemma"]=="nemnan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["prefix"]=="ge")]))
		write_tex("nemnan_perf_ein_bsp_0_Chr", write_example(perf_df[(perf_df["lemma"]=="nemnan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["prefix"]=="0")].iloc[:1]))
		write_tex("nemnan_perf_ein_bsp_ga_Chr", write_example(perf_df[(perf_df["lemma"]=="nemnan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["prefix"]=="ge")].iloc[:1]))
		write_tex("nemnan_perf_bsp_ga_Mrv", write_example(perf_df[(perf_df["lemma"]=="nemnan") & ~(perf_df["doc"].str.match("Chronicle"))]))
		
		#lm=hātan
		write_tex("hatan_perf_by_doc", write_table_by_doc(perf_df[perf_df["lemma"]=="hātan"]))
		write_tex("hatan_perf_by_doc", write_table_by_doc(perf_df[perf_df["lemma"]=="hātan"]))
		write_tex("hatan_perf_by_sem", write_table_by_col(perf_df[perf_df["lemma"]=="hātan"], "sem"))
		
		write_tex("hatan_perf_ein_bsp_0_Or", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["prefix"]=="0") & (perf_df["doc"].str.match("Orosius"))].iloc[:1]))
		write_tex("hatan_perf_bsp_ga_Or", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["prefix"]=="ge") & (perf_df["doc"].str.match("Orosius"))]))
	
		write_tex("hatan_bsp_perf_versprechen_Or", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"]=="Orosius") & (perf_df["sem"]=="versprechen")]))
		write_tex("hatan_bsp_perf_nennen_Or_ga", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"]=="Orosius") & (perf_df["sem"]=="nennen") & (perf_df["prefix"]=="ge")]))
		write_tex("hatan_bsp_perf_nennen_app_Chr_ga", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"]=="Chronicle") & (perf_df["sem"]=="nennen") & (perf_df["prefix"]=="ge") & (perf_df["clause"]=="app")]))
		write_tex("hatan_bsp_perf_nennen_app_Chr_0", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"]=="Chronicle") & (perf_df["sem"]=="nennen") & (perf_df["prefix"]=="0") & (perf_df["clause"]=="app")]))
		
		write_tex("hatan_perf_bsp_Chr", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"].str.match("Chronicle"))].sort_values(["prefix"])))
		write_tex("hatan_perf_zwei_bsp_Chr", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["line"].isin([1297, 1317]))], True))
		write_tex("hatan_perf_ein_bsp_Chr", write_example(perf_df[(perf_df["lemma"]=="hātan") & (perf_df["doc"].str.match("Chronicle")) & (perf_df["line"].isin([585]))], True))
		
		#lm=singan
		write_tex("singan_perf_count", write_table_by_doc(perf_df[perf_df["lemma"]=="singan"]))
		write_tex("singan_perf_bsp", write_example(perf_df[perf_df["lemma"]=="singan"], True))
		write_tex("singan_ein_bsp_perf_ga", write_example(perf_df[(perf_df["lemma"]=="singan") & (perf_df["prefix"]=="ge")].iloc[:1], True))
		write_tex("singan_ein_bsp_perf_0", write_example(perf_df[(perf_df["lemma"]=="singan") & (perf_df["prefix"]=="0")].iloc[:1], True))
		
		write_tex("faran_perf_bsp_Chron", write_example(perf_df[(perf_df["lemma"]=="faran") & (perf_df["doc"]=="Chronicle")]))
		write_tex("faran_perf_bsp_Ælfric", write_example(perf_df[(perf_df["lemma"]=="faran") & (perf_df["doc"]=="Letters")]))
		write_tex("faran_perf_ein_bsp_Ælfric", write_example(perf_df[(perf_df["lemma"]=="faran") & (perf_df["doc"]=="Letters")].iloc[:1]))
		write_tex("faran_perf_bsp_Or", write_example(perf_df[(perf_df["lemma"]=="faran") & (perf_df["doc"]=="Orosius")]))
		write_tex("faran_perf_ein_bsp_Or", write_example(perf_df[(perf_df["lemma"]=="faran") & (perf_df["doc"]=="Orosius") & (perf_df["line"]==412)]))
	write_perfekt()
			
	exclude = ["aux", "keep", "modalverb"]
	exclude_strict = exclude + ["unpräf"]
	
	df = df[~(df["status"].str.match("^(fest|q-hapax|hapax)$"))]
	dauern = "lange|simle|dæġ|oft|oftr\\textaemacron{}dlīċe"
	#Auflistung aller Lemmata absteigend sortiert nach Gesamtzahl der Belege
	
	write_tex("flexible_lemma_count_old", lemma_pivot(df[(~df["status"].isin(exclude)) & ((df["prefix"]=="ge") | (df["prefix"]=="0"))], sort="total"))
	write_tex("onginnan_to", write_table_by_lemma(df[df["rektion"].str.match(".*ginnan")]))
	write_tex("prs_lemma_count", lemma_pivot(df[(df["g_kat"].isin(["prs", "ger"])) & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, no_zero=True))
	write_tex("prt_lemma_count", lemma_pivot(df[(df["g_kat"]=="prt") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(["fest", "hapax", "q-hapax"]))], no_zero=True))
	
	write_tex("prt_flexible_lemma_count", lemma_pivot(df[(df["g_kat"]=="prt")], incl_pref=True, incl_zero=True))
	
	inf_df = df[(df["gram"]=="inf.")].copy()
	inf_df["negation"] = inf_df["negation"].apply(lambda x: "negiert" if not x == "0" else x)
	write_tex("infinitiv_by_neg", write_table_by_col(inf_df, "negation"))
	
	def write_lemma():	
		#Lemmaspezifsche Auszählungen
		def write_motion():
			#faran
			faran_df = df[df["lemma"]=="faran"]
			write_tex("faran_by_gram", write_table_by_grammar(faran_df))
			write_tex("faran_by_sem", write_table_by_col(faran_df, "sem"))
			write_tex("faran_bsp_perf", write_example(faran_df[faran_df["g_kat"]=="perf"]))
			write_tex("faran_ein_bsp_sterben", write_example(faran_df[faran_df["sem"]=="sterben"].iloc[:1]))
			write_tex("faran_akk", write_table_by_col(faran_df[faran_df["obj_case"]=="akk"], "prefix"))
			write_tex("faran_ein_bsp_akk_ga", write_example(faran_df[(faran_df["obj_case"]=="akk") & (faran_df["prefix"]=="ge") & (faran_df["line"].isin([683]))]))
			write_tex("faran_zwei_bsp_akk_ga", write_example(faran_df[(faran_df["obj_case"]=="akk") & (faran_df["prefix"]=="ge") & (faran_df["line"].isin([1580, 683]))]))
			write_tex("faran_bsp_on+a_0", write_example(faran_df[(faran_df["sem"]=="motion") & (faran_df["pr_obj"]=="on+a") & (faran_df["prefix"]=="0")]))
			write_tex("faran_bsp_prt_on+a_0", write_example(faran_df[(faran_df["sem"]=="motion") & (faran_df["pr_obj"]=="on+a") & (faran_df["prefix"]=="0") & (faran_df["g_kat"]=="prt")]))
			write_tex("faran_ein_bsp_on+a_0", write_example(faran_df[(faran_df["sem"]=="motion") & (faran_df["pr_obj"]=="on+a") & (faran_df["prefix"]=="0") & (faran_df["line"]==754)].iloc[:1]))
			write_tex("faran_ein_bsp_on+a_ga", write_example(faran_df[(faran_df["sem"]=="motion") & (faran_df["pr_obj"]=="on+a") & (faran_df["prefix"]=="ge")].iloc[:1]))
			
			write_tex("geforþferan", write_example(df[df["match"]=="geforþferde"]))
			
			gan_df = df[df["lemma"]=="gān"]
			write_tex("gan_by_gram", write_table_by_grammar(gan_df))
			write_tex("gan_ein_bsp_akk", write_example(gan_df[(gan_df["obj_case"]=="akk") & (gan_df["line"].isin([10, 12]))], condense=True))
			
			ridan_df = df[df["lemma"]=="rīdan"]
			write_tex("ridan_ein_bsp_akk", write_example(ridan_df[(ridan_df["line"].isin([1007, 1009]))], condense=True))
			
		write_motion()
		
		write_tex("motion_bsp_ga", write_example(df[(df["sem"]=="motion") & ~(df["status"]=="fest") & ~(df["g_kat"]=="perf") & (df["prefix"]=="ge")].sort_values("lemma"), True))
		def write_performative():
			#dōn
			don_df = df[df["lemma"].isin(["dōn", "ġedōn"])]
			write_tex("don_by_gram", write_table_by_grammar(don_df))
			write_tex("don_by_doc", write_table_by_doc(don_df))
			write_tex("don_by_obj", write_table_by_col(don_df[~(don_df["g_kat"]=="perf")], "object"))
			write_tex("don_by_sem", write_table_by_col(don_df[~(don_df["g_kat"]=="perf")], "sem"))
			
			write_tex("don_bsp_0_ga", write_example(don_df[(don_df["object"]=="0") & (don_df["prefix"]=="ge")]))
			write_tex("don_bsp_to_gode_0", write_example(don_df[(don_df["pr_obj"]=="tō+") & ~(don_df["sem"].isin(["put", "faktitiv"])) & (don_df["prefix"]=="0")]))
			write_tex("don_bsp_dass", write_example(don_df[(don_df["object"]=="dassSatz")]))
			write_tex("don_zwei_bsp_dass", write_example(don_df[(don_df["object"]=="dassSatz") & (don_df["line"].isin([411, 72]))]))
			write_tex("don_bsp_aci", write_example(don_df[(don_df["object"]=="AcI")]))
			write_tex("don_bsp_unþanc", write_example(don_df[(don_df["adjunct"]=="unþanc")]))
			write_tex("don_bsp_bileofa", write_example(don_df[(don_df["adjunct"]=="bīleofa")]))
			write_tex("don_bsp_dædbot", write_example(don_df[(don_df["adjunct"]=="d\\textaemacron{}dbōt")]))
			write_tex("don_bsp_yfel_ga", write_example(don_df[(don_df["adjunct"]=="yfel") & (don_df["prefix"]=="ge")]))
			write_tex("don_bsp_yfel_0", write_example(don_df[(don_df["adjunct"]=="yfel") & (don_df["prefix"]=="0")]))
			write_tex("don_zwei_bsp_yfel_0", write_example(don_df[(don_df["adjunct"]=="yfel") & (don_df["prefix"]=="0") & (don_df["line"]<50)]))
			write_tex("don_bsp_unbel", write_example(don_df[(don_df["adjunct"].isin(["gōd", "lāþ", "synn"]))]))
			
			write_tex("don_bsp_pro_ga", write_example(don_df[(don_df["sem"]=="empty") & ~(don_df["g_kat"]=="perf") & ~(don_df["object"]=="0") & (don_df["prefix"]=="ge")], condense=True))
			write_tex("don_bsp_faktitiv_0", write_example(don_df[(don_df["sem"]=="faktitiv") & (don_df["prefix"]=="0") & (don_df["object"].isin(["prn", "sub"]))]))
			write_tex("don_bsp_faktitiv_prp_ga", write_example(don_df[~(don_df["sem"]=="empty") & ~(don_df["pr_obj"].isin(["", "dat"])) & (don_df["prefix"]=="ge") & (don_df["object"].isin(["prn", "sub"]))]))
			write_tex("don_ein_bsp_faktitiv_prp_ga", write_example(don_df[~(don_df["sem"]=="empty") & ~(don_df["pr_obj"].isin(["", "dat"])) & (don_df["prefix"]=="ge") & (don_df["object"].isin(["prn", "sub"])) & (don_df["line"].isin([70]))]))
			write_tex("don_zwei_bsp_faktitiv_prp_ga", write_example(don_df[~(don_df["sem"]=="empty") & ~(don_df["pr_obj"].isin(["", "dat"])) & (don_df["prefix"]=="ge") & (don_df["object"].isin(["prn", "sub"])) & (don_df["line"].isin([70, 676]))]))
			write_tex("don_bsp_faktitiv_akk_ga", write_example(don_df[(don_df["sem"]=="faktitiv") & (don_df["pr_obj"]=="") &(don_df["prefix"]=="ge") & (don_df["object"].isin(["prn", "sub"]))]))
			write_tex("don_ein_bsp_faktitiv_akk_ga", write_example(don_df[(don_df["sem"]=="faktitiv") & (don_df["pr_obj"]=="") &(don_df["prefix"]=="ge") & (don_df["object"].isin(["prn", "sub"])) & (don_df["line"].isin([673]))]))
			write_tex("don_bsp_put", write_example(don_df[(don_df["sem"]=="put")]))
			write_tex("don_ein_bsp_put", write_example(don_df[(don_df["sem"]=="put")].iloc[:1]))
			write_tex("don_bsp_eval", write_example(don_df[(don_df["sem"]=="eval")]))
			write_tex("don_ein_bsp_eval", write_example(don_df[(don_df["sem"]=="eval") & (don_df["line"]==775)]))
			
			
			#macian
			macian_df = df[df["lemma"]=="macian"]
			write_tex("macian_by_gram", write_table_by_grammar(macian_df))
			write_tex("macian_bsp_prt_ga", write_example(macian_df[(macian_df["prefix"]=="ge") & (macian_df["g_kat"]=="prt")]))
			write_tex("macian_bsp_prt_0", write_example(macian_df[(macian_df["prefix"]=="0") & (macian_df["g_kat"]=="prt")]))
			write_tex("macian_bsp_prs_ga", write_example(macian_df[(macian_df["prefix"]=="ge") & (macian_df["g_kat"]=="prs")]))
			write_tex("macian_bsp_inf_0", write_example(macian_df[(macian_df["prefix"]=="0") & (macian_df["g_kat"]=="inf")]))
			
			#fremman
			fremman_df = df[df["lemma"].isin(["fremman", "ġefremman"])]
			write_tex("fremman_by_gram", write_table_by_grammar(fremman_df))
			write_tex("fremman_by_doc", write_table_by_doc(fremman_df))
			write_tex("fremman_bsp_inf", write_example(fremman_df[fremman_df["g_kat"]=="inf"]))
			write_tex("fremman_bsp_prs", write_example(fremman_df[fremman_df["g_kat"]=="prs"]))
			write_tex("fremman_bsp_ind_prs", write_example(fremman_df[(fremman_df["g_kat"]=="prs") & (fremman_df["mood"]=="ind")]))
			write_tex("fremman_bsp_prt", write_example(fremman_df[fremman_df["g_kat"]=="prt"]))
			
			
			#biddan
			biddan_df = df[df["lemma"]=="biddan"]
			write_tex("biddan_by_gram", write_table_by_grammar(biddan_df))
			write_tex("biddan_bsp_dass", write_example(biddan_df[biddan_df["object"]=="dassSatz"].iloc[0:1,:]))
			write_tex("biddan_bsp_Maria", write_example(biddan_df[(biddan_df["object"]=="dassSatz") & (biddan_df["adjunct"]=="npr.")].iloc[0:1,:]))
			write_tex("biddan_bsp_HS", write_example(biddan_df[biddan_df["object"]==":"].iloc[0:1,:]))
			write_tex("biddan_bsp_gen", write_example(biddan_df[biddan_df["obj_case"]=="gen"].iloc[0:1,:]))
			biddan_rest_df = biddan_df[~(biddan_df["object"].isin(["dassSatz", ":"])) & ~(biddan_df["obj_case"]=="gen")]
			write_tex("biddan_rest_by_doc", write_table_by_grammar(biddan_rest_df))
			write_tex("biddan_bsp_prn", write_example(biddan_rest_df[(biddan_rest_df["object"].isin(["prn", "sub"]))]))
			write_tex("biddan_bsp_0", write_example(biddan_rest_df[(biddan_rest_df["object"].isin(["0"])) & ~(biddan_rest_df["adjunct"].isin(["refl"]))]))
			write_tex("biddan_bsp_refl", write_example(biddan_rest_df[(biddan_rest_df["adjunct"].isin(["refl"]))]))
			write_tex("biddan_ein_bsp_refl", write_example(biddan_rest_df[(biddan_rest_df["adjunct"].isin(["refl"]))].iloc[:1]))
			write_tex("biddan_bsp_for", write_example(biddan_rest_df[biddan_rest_df["pr_obj"].isin(["for+"])].iloc[0:1,:]))
			
			#grētan
			gretan_df = df[df["lemma"]=="grētan"]
			write_tex("gretan_by_gram", write_table_by_grammar(gretan_df))
			write_tex("gretan_bsp_ga", write_example(gretan_df[(gretan_df["prefix"]=="ge") & ~(gretan_df["g_kat"]=="perf")]))
			write_tex("gretan_bsp_0", write_example(gretan_df[(gretan_df["prefix"]=="0") & ~(gretan_df["g_kat"]=="perf")]))
			
			#stillan
			stillan_df = df[df["lemma"]=="stillan"]
			write_tex("stillan_by_gram", write_table_by_grammar(stillan_df))
			
			#bēodan
			beodan_df = df[df["lemma"]=="bēodan"]
			write_tex("beodan_by_gram", write_table_by_grammar(beodan_df))
			write_tex("beodan_by_doc", write_table_by_doc(beodan_df))
			write_tex("beodan_by_sem", write_table_by_col(beodan_df, "sem"))
			write_tex("beodan_bsp_prs", write_example(beodan_df[beodan_df["g_kat"]=="prs"]))
			write_tex("beodan_bsp_prt_ga", write_example(beodan_df[(beodan_df["g_kat"]=="prt") & (beodan_df["prefix"]=="ge")]))
			write_tex("beodan_bsp_prt_0", write_example(beodan_df[(beodan_df["g_kat"]=="prt") & (beodan_df["prefix"]=="0")]))
			write_tex("beodan_bsp_ga_Chron", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="ge") & (beodan_df["doc"]=="Chronicle")]))
			write_tex("beodan_ein_bsp_ga_Chron", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="ge") & (beodan_df["doc"]=="Chronicle")].iloc[:1]))
			write_tex("beodan_bsp_ga_Ælf", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="ge") & (beodan_df["doc"]=="Prefaces")]))
			write_tex("beodan_bsp_ga_sem1", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="ge") & (beodan_df["sem"]=="anbieten")]))
			write_tex("beodan_ein_bsp_gebieten", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["sem"]=="gebieten") & (beodan_df["line"]==1461)]))
			write_tex("beodan_bsp_0_sem1", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="0") & (beodan_df["sem"]=="anbieten")]))
			write_tex("beodan_ein_bsp_0_sem1", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="0") & (beodan_df["sem"]=="anbieten")].iloc[:1]))
			write_tex("beodan_ander_bsp_0_sem1", write_example(beodan_df[~(beodan_df["g_kat"]=="perf") & (beodan_df["prefix"]=="0") & (beodan_df["sem"]=="anbieten") & (beodan_df["line"]==1493)]))
			
			#offrian
			offrian_df = df[df["lemma"]=="offrian"]
			write_tex("offrian_by_gram", write_table_by_grammar(offrian_df))
			write_tex("offrian_bsp_prt", write_example(offrian_df[(offrian_df["g_kat"]=="prt")]))
			write_tex("offrian_bsp_prt_ga", write_example(offrian_df[(offrian_df["g_kat"]=="prt") & (offrian_df["prefix"]=="ge")]))
			write_tex("offrian_ein_bsp_prt_0", write_example(offrian_df[(offrian_df["g_kat"]=="prt") & (offrian_df["prefix"]=="0")].iloc[:1]))
			write_tex("offrian_bsp_imp", write_example(offrian_df[(offrian_df["tempus"]=="prs") & (offrian_df["line"]<26)], condense=True))
			write_tex("offrian_bsp_prs", write_example(offrian_df[(offrian_df["g_kat"]=="prs")]))
			write_tex("offrian_bsp_prs_ga", write_example(offrian_df[(offrian_df["g_kat"]=="prs") & (offrian_df["prefix"]=="ge")]))
			write_tex("offrian_bsp_prs_0", write_example(offrian_df[(offrian_df["g_kat"]=="prs") & (offrian_df["prefix"]=="0")]))
			write_tex("offrian_ein_bsp_prs_0", write_example(offrian_df[(offrian_df["g_kat"]=="prs") & (offrian_df["prefix"]=="0") & (offrian_df["line"]==309)]))
			write_tex("offrian_bsp_inf", write_example(offrian_df[(offrian_df["g_kat"]=="inf")]))
			write_tex("offrian_bsp_inf_ga", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="ge")]))
			write_tex("offrian_bsp_inf_0", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="0")]))
			write_tex("offrian_ein_bsp_inf_Isaac_ga", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="ge") & (offrian_df["line"].isin([224]))]))
			write_tex("offrian_ein_bsp_inf_Isaac_0", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="0") & (offrian_df["line"].isin([217]))]))
			write_tex("offrian_bsp_inf_sculan_ga", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="ge") & (offrian_df["rektion"]=="sculan")]))
			write_tex("offrian_bsp_inf_sculan_0", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="0") & (offrian_df["rektion"]=="sculan")]))
			write_tex("offrian_ein_bsp_inf_sculan_ga", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="ge") & (offrian_df["rektion"]=="sculan") & (offrian_df["line"]==370)]))
			write_tex("offrian_ein_bsp_inf_sculan_0", write_example(offrian_df[(offrian_df["g_kat"]=="inf") & (offrian_df["prefix"]=="0") & (offrian_df["rektion"]=="sculan")].iloc[:1]))
			
			#fultumian
			fultumian_df = df[df["lemma"]=="fultumian"]
			write_tex("fultumian_by_gram", write_table_by_grammar(fultumian_df))
			write_tex("fultumian_bsp_0", write_example(fultumian_df[fultumian_df["prefix"]=="0"]))
			write_tex("fultumian_bsp_prs", write_example(fultumian_df[fultumian_df["tempus"]=="prs"]))
			write_tex("fultumian_bsp_inf", write_example(fultumian_df[fultumian_df["g_kat"]=="inf"]))
			write_tex("fultumian_bsp_prt_ga", write_example(fultumian_df[(fultumian_df["g_kat"]=="prt") & (fultumian_df["prefix"]=="ge")]))
			write_tex("fultumian_ein_bsp_prt_ga", write_example(fultumian_df[(fultumian_df["g_kat"]=="prt") & (fultumian_df["prefix"]=="ge")].iloc[:1]))
			
			#helpan
			helpan_df = df[df["lemma"]=="helpan"]
			write_tex("helpan_by_gram", write_table_by_grammar(helpan_df))
			write_tex("helpan_bsp_imp", write_example(helpan_df[helpan_df["mood"]=="imp"]))
			write_tex("helpan_bsp_inf", write_example(helpan_df[helpan_df["mood"]=="inf"]))
			write_tex("helpan_bsp_prt", write_example(helpan_df[helpan_df["g_kat"]=="prt"]))
			write_tex("helpan_bsp_prs", write_example(helpan_df[(helpan_df["g_kat"]=="prs")]))
			
		write_performative()
		
		def write_durative():
			#feohtan
			feohtan_df = df[df["lemma"]=="feohtan"].copy()
			write_tex("feohtan_by_gram", write_table_by_grammar(feohtan_df))
			write_tex("feohtan_by_doc", write_table_by_doc(feohtan_df))
			write_tex("feohtan_wiþ_by_case", write_table_by_col(feohtan_df[(feohtan_df["pr_obj"].str.contains("wiþ")) & (feohtan_df["doc"]=="Chronicle")], "pr_obj"))
			write_tex("chi2_feohtan_wiþ_by_case", chi2(feohtan_df[(feohtan_df["pr_obj"].str.contains("wiþ")) & (feohtan_df["doc"]=="Chronicle")], "pr_obj", "prefix"))
			
			write_tex("feohtan_bsp_akk_ga", write_example(feohtan_df[(feohtan_df["obj_case"]=="akk") & (feohtan_df["prefix"]=="ge")]))
			write_tex("feohtan_bsp_akk_ga_count", write_example(feohtan_df[(feohtan_df["obj_case"]=="akk") & (feohtan_df["prefix"]=="ge")], return_number=True))
			write_tex("feohtan_zwei_bsp_akk_ga", write_example(feohtan_df[(feohtan_df["obj_case"]=="akk") & (feohtan_df["prefix"]=="ge") & (feohtan_df["line"].isin([1120, 293]))]))
			write_tex("feohtan_bsp_on_akk", write_example(feohtan_df[(feohtan_df["pr_obj"].str.contains("on\+a", regex=True))]))
			write_tex("feohtan_bsp_on_akk_0_count", write_example(feohtan_df[(feohtan_df["pr_obj"].str.contains("on\+a", regex=True)) & (feohtan_df["prefix"]=="0")], return_number=True))
			write_tex("feohtan_zwei_bsp_on_akk", write_example(feohtan_df[(feohtan_df["pr_obj"].str.contains("on\+a", regex=True)) & (feohtan_df["line"].isin([1585, 653]))]))
			write_tex("feohtan_bsp_þær_on", write_example(feohtan_df[(feohtan_df["adverb_tmp"].str.contains("^on,?(?!{})", regex=True))]))
			write_tex("feohtan_bsp_temp_adv", write_example(feohtan_df[(feohtan_df["adverb_tmp"].str.contains(dauern, regex=True))]))
			write_tex("feohtan_bsp_temp_adv_0_count", write_example(feohtan_df[(feohtan_df["adverb_tmp"].str.contains(dauern, regex=True)) & (feohtan_df["prefix"]=="0")], return_number=True))
			write_tex("feohtan_zwei_bsp_temp_adv", write_example(feohtan_df[(feohtan_df["adverb_tmp"].str.contains(dauern, regex=True)) & (feohtan_df["line"].isin([1605, 601]))]))
			write_tex("feohtan_bsp_inf_0", write_example(feohtan_df[(feohtan_df["g_kat"]=="inf") & (feohtan_df["prefix"]=="0")]))
			write_tex("feohtan_bsp_rezip", write_example(feohtan_df[(feohtan_df["object"]=="0") & (feohtan_df["number"]=="pl") & (feohtan_df["adverb_tmp"].isin(["", "þ\\textymacron{}", "þā"]))]))
			write_tex("feohtan_bsp_rezip_ga_count", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["object"]=="0") & (feohtan_df["number"]=="pl") & (feohtan_df["adverb_tmp"].isin(["", "þ\\textymacron{}", "þā"]))], return_number=True))
			write_tex("feohtan_zwei_bsp_rezip_ga", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["object"]=="0") & (feohtan_df["number"]=="pl") & (feohtan_df["adverb_tmp"].isin(["", "þ\\textymacron{}", "þā"]))].iloc[:2]))
			write_tex("feohtan_bsp_wiþ_sg_by_adj", write_table_by_col(feohtan_df[(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan", "him"])) & (feohtan_df["g_kat"]=="prt")], "adjunct"))
			write_tex("feohtan_bsp_wiþ_sg_0", write_example(feohtan_df[(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan", "him"])) & (feohtan_df["g_kat"]=="prt") & (feohtan_df["prefix"]=="0")]))
			write_tex("feohtan_bsp_wiþ_sg_0_count", write_example(feohtan_df[(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan", "him"])) & (feohtan_df["g_kat"]=="prt") & (feohtan_df["prefix"]=="0")], return_number=True))
			write_tex("feohtan_bsp_wiþ_sg_ga", write_example(feohtan_df[(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan", "him"])) & (feohtan_df["g_kat"]=="prt") & (feohtan_df["prefix"]=="ge")]))
			write_tex("feohtan_bsp_wiþ_sg_ga_count", write_example(feohtan_df[(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan", "him"])) & (feohtan_df["g_kat"]=="prt") & (feohtan_df["prefix"]=="ge")], return_number=True))
			
			feohtan_df = feohtan_df[~(feohtan_df["obj_case"]=="akk")]
			write_tex("feohtan_prt_by_doc", write_table_by_doc(feohtan_df[(feohtan_df["g_kat"]=="prt")]))
			write_tex("feohtan_bsp_prt_0_ga", write_example(feohtan_df[(feohtan_df["g_kat"]=="prt") & (feohtan_df["object"]=="0") & (feohtan_df["prefix"]=="ge")]))
			write_tex("feohtan_bsp_prt_0_0", write_example(feohtan_df[(feohtan_df["g_kat"]=="prt") & (feohtan_df["object"]=="0") & (feohtan_df["prefix"]=="0")]))
			
			write_tex("feohtan_Or_by_prp", write_table_by_col(feohtan_df[(feohtan_df["doc"]=="Orosius") & (feohtan_df["g_kat"]=="prt") & (feohtan_df["object"]=="")], "pr_obj"))
			write_tex("feohtan_Chr_by_prp", write_table_by_col(feohtan_df[(feohtan_df["doc"]=="Chronicle") & (feohtan_df["g_kat"]=="prt") & (feohtan_df["object"]=="")], "pr_obj"))
			
			feohtan_df = feohtan_df[(feohtan_df["doc"]=="Chronicle") & (feohtan_df["g_kat"]=="prt") & ~(feohtan_df["obj_case"]=="akk") & ~(feohtan_df["pr_obj"].str.contains("on\+a")) & ~(feohtan_df["adverb_tmp"].str.contains(r"\bon", regex=True)) & ~(feohtan_df["adverb_tmp"].str.contains(dauern)) & ~(feohtan_df["adjunct"].isin(["cyning", "npr.", "ealdormann", "here", "Pendan"]))]
			feohtan_df.loc[:,"year_group"] = feohtan_df.loc[:,"year"].apply(lambda x: (int(x)//100)*100)
			write_tex("feohtan_by_years", write_table_by_col(feohtan_df, "year_group"))
			write_tex("feohtan_bsp_400_ga", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["year_group"]==400)], condense=True))
			write_tex("feohtan_bsp_400_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==400)], condense=True))
			write_tex("feohtan_bsp_500_ga", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["year_group"]==500)], condense=True))
			write_tex("feohtan_bsp_500_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==500)], condense=True))
			write_tex("feohtan_bsp_600_ga", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["year_group"]==600)], condense=True))
			write_tex("feohtan_bsp_600_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==600)], condense=True))
			write_tex("feohtan_bsp_700_ga", write_example(feohtan_df[(feohtan_df["prefix"]=="ge") & (feohtan_df["year_group"]==700)], condense=True))
			write_tex("feohtan_bsp_700_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==700)], condense=True))
			write_tex("feohtan_bsp_800_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==800)], condense=True))
			write_tex("feohtan_bsp_900_0", write_example(feohtan_df[(feohtan_df["prefix"]=="0") & (feohtan_df["year_group"]==900)], condense=True))
			write_tex("biserial_feohtan_year", r_pb(feohtan_df, "year"))
			
			write_tex("feohtan_prt_zwei_bsp", write_example(feohtan_df[(feohtan_df["gram"].str.match(".+(ind|cnj)\.prt\.")) & (feohtan_df["line"].isin([266, 279]))], True))
			write_tex("feohtan_prt_bsp", write_example(feohtan_df[(feohtan_df["gram"].str.match(".+(ind|cnj)\.prt\."))]))
			
			#winnan
			winnan_df = df[df["lemma"]=="winnan"]
			write_tex("winnan_by_gram", write_table_by_grammar(winnan_df))
			write_tex("winnan_bsp_inf_ga", write_example(winnan_df[(winnan_df["g_kat"]=="inf") & (winnan_df["prefix"]=="ge")]))
			write_tex("winnan_bsp_inf_akk_0", write_example(winnan_df[(winnan_df["g_kat"]=="inf") & (winnan_df["obj_case"]=="akk") & (winnan_df["prefix"]=="0")]))
			write_tex("winnan_bsp_prt_akk_ga", write_example(winnan_df[(winnan_df["g_kat"]=="prt") & (winnan_df["obj_case"]=="akk") & (winnan_df["prefix"]=="ge")]))
			write_tex("winnan_bsp_prt_wiþ_ga", write_example(winnan_df[(winnan_df["g_kat"]=="prt") & (winnan_df["pr_obj"].str.contains("wiþ+")) & (winnan_df["prefix"]=="ge")]))
			write_tex("winnan_bsp_prt_wiþ_0", write_example(winnan_df[(winnan_df["g_kat"]=="prt") & (winnan_df["pr_obj"].str.contains("wiþ+")) & (winnan_df["clause"]=="HS") & (winnan_df["prefix"]=="0")]))
			
			#lǣdan
			laedan_df = df[df["lemma"]=="l\\textaemacron{}dan"]
			write_tex("laedan_by_gram", write_table_by_grammar(laedan_df))
			write_tex("laedan_by_doc", write_table_by_doc(laedan_df))
			write_tex("laedan_bsp_prt_ga", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["prefix"]=="ge")]))
			write_tex("laedan_bsp_prt_0", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["prefix"]=="0")]))
			write_tex("laedan_ein_bsp_prt_ga_Chron", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Chronicle") & (laedan_df["prefix"]=="ge")]))
			write_tex("laedan_ein_bsp_prt_ga_Ælf", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"].isin(["Letters", "Prefaces", "Catholic Homilies"])) & (laedan_df["prefix"]=="ge")].iloc[:1]))
			write_tex("laedan_ein_bsp_prt_ga_Or", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Orosius") & (laedan_df["prefix"]=="ge")].iloc[:1]))
			write_tex("laedan_ein_bsp_prt_0_Chron", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Chronicle") & (laedan_df["prefix"]=="0")].iloc[:1]))
			write_tex("laedan_ein_bsp_prt_0_Ælf", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"].isin(["Letters", "Prefaces", "Catholic Homilies"])) & (laedan_df["prefix"]=="0")]))
			write_tex("laedan_ein_bsp_prt_0_Or", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Orosius") & (laedan_df["prefix"]=="0")]))
			write_tex("laedan_bsp_Feldzug", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["sem"]=="Feldzug")]))
			write_tex("laedan_bsp_Gefangener", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["sem"]=="Gefangener")].sort_values(["prefix"])))
			write_tex("laedan_bsp_führen", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["sem"]=="führen")]))
			write_tex("laedan_bsp_anführen", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["sem"]=="anführen")]))
			write_tex("laedan_bsp_Chr_Feldzug", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["sem"]=="Feldzug") & (laedan_df["doc"]=="Chronicle")].sort_values("prefix", ascending=False)))
			write_tex("laedan_bsp_Or", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Orosius")]))
			write_tex("laedan_bsp_Letters", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Letters")].sort_values("prefix")))
			write_tex("laedan_bsp_Chr", write_example(laedan_df[(laedan_df["g_kat"]=="prt") & (laedan_df["doc"]=="Chronicle")]))
			
			#hergian
			hergian_df = df[df["lemma"]=="hergian"]
			write_tex("hergian_by_gram", write_table_by_grammar(hergian_df))
			write_tex("hergian_by_doc", write_table_by_doc(hergian_df))
			write_tex("hergian_by_number", write_table_by_col(hergian_df[~(hergian_df["g_kat"].isin(["perf", "ger"]))], "number"))
			write_tex("hergian_bsp_prt_ga", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["prefix"]=="ge")]))
			write_tex("hergian_ein_bsp_prt_ga", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["prefix"]=="ge") & (hergian_df["line"]<417)], condense=True))
			write_tex("hergian_bsp_prt_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["prefix"]=="0")]))
			write_tex("hergian_bsp_prt_sg_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["number"]=="sg") & (hergian_df["prefix"]=="0")]))
			write_tex("hergian_paar_bsp_prt_sg_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["number"]=="sg") & (hergian_df["prefix"]=="0") & (hergian_df["line"].isin([980, 874]))]))
			write_tex("hergian_bsp_prt_pl_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["number"]=="pl") & (hergian_df["prefix"]=="0")]))
			write_tex("hergian_ein_bsp_prt_pl_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["number"]=="pl") & (hergian_df["prefix"]=="0") & (hergian_df["line"].isin([1453]))]))
			write_tex("hergian_paar_bsp_prt_pl_0", write_example(hergian_df[(hergian_df["g_kat"]=="prt") & (hergian_df["number"]=="pl") & (hergian_df["prefix"]=="0") & (hergian_df["line"].isin([1453, 1494]))]))
			write_tex("hergian_bsp_prt_Chr_0", write_example(hergian_df[(hergian_df["doc"]=="Chronicle") & (hergian_df["g_kat"]=="prt") & (hergian_df["prefix"]=="0")]))
			write_tex("hergian_bsp_Or", write_example(hergian_df[(hergian_df["doc"]=="Orosius")]))
			write_tex("hergian_bsp_Letters", write_example(hergian_df[(hergian_df["doc"]=="Letters")]))
			
			#leben
			libban_df = df[df["lemma"]=="libban"]
			lifian_df = df[df["lemma"]=="lifian"]
			write_tex("libban_by_gram", write_table_by_grammar(libban_df))
			write_tex("lifian_by_gram", write_table_by_grammar(lifian_df))
			write_tex("libban_bsp_ga", write_example(libban_df[libban_df["prefix"]=="ge"]))
			write_tex("libban_bsp_ger", write_example(libban_df[libban_df["g_kat"]=="ger"].iloc[:1]))
			write_tex("lifian_bsp_ger", write_example(lifian_df[lifian_df["g_kat"]=="ger"].iloc[:1]))
			
			#wīcian
			wician_df = df[df["lemma"]=="wīcian"]
			write_tex("wician_by_gram", write_table_by_grammar(wician_df))
			write_tex("wician_by_doc", write_table_by_doc(wician_df))
			wician_df = wician_df[~(wician_df["g_kat"]=="perf")]
			write_tex("wician_bsp_ga", write_example(wician_df[wician_df["prefix"]=="ge"]))
			write_tex("wician_bsp_0", write_example(wician_df[wician_df["prefix"]=="0"]))
			write_tex("wician_ein_bsp_0", write_example(wician_df[(wician_df["prefix"]=="0") & (wician_df["line"]==1514)]))
			
			#restan
			restan_df = df[df["lemma"]=="restan"]
			write_tex("restan_by_gram", write_table_by_grammar(restan_df))
			write_tex("restan_bsp_inf", write_example(restan_df[restan_df["g_kat"]=="inf"]))
			
			#sittan
			sittan_df = df[df["lemma"]=="sittan"]
			write_tex("sittan_by_gram", write_table_by_grammar(sittan_df))
			write_tex("sittan_by_doc", write_table_by_doc(sittan_df))
			write_tex("sittan_bsp_intr_ga", write_example(sittan_df[(sittan_df["prefix"]=="ge") & (sittan_df["object"]=="0")]))
			write_tex("sittan_ein_bsp_akk_ga", write_example(sittan_df[(sittan_df["prefix"]=="ge") & (sittan_df["object"]=="sub")].iloc[:1]))
			write_tex("sittan_bsp_akk_0", write_example(sittan_df[(sittan_df["prefix"]=="0") & (sittan_df["object"]=="sub")]))
			write_tex("sittan_bsp_prp_ga", write_example(sittan_df[(sittan_df["prefix"]=="ge") & ~(sittan_df["pr_obj"]=="")]))
			write_tex("sittan_ein_bsp_prp_ga", write_example(sittan_df[(sittan_df["prefix"]=="ge") & ~(sittan_df["pr_obj"]=="")].iloc[:1]))
			
			#bīdan
			bidan_df = df[df["lemma"]=="bīdan"]
			write_tex("bidan_by_gram", write_table_by_grammar(bidan_df))
			write_tex("bidan_bsp_ga", write_example(bidan_df[(bidan_df["prefix"]=="ge") & ~(bidan_df["g_kat"]=="perf")]))
			write_tex("bidan_bsp_0", write_example(bidan_df[(bidan_df["prefix"]=="0") & ~(bidan_df["g_kat"]=="perf")]))
		write_durative()
		
		def write_telic():
			def concrete():
				#wyrċan
				wyrcan_df = df[df["lemma"]=="wyrċan"]
				write_tex("wyrcan_by_gram", write_table_by_grammar(wyrcan_df))
				write_tex("wyrcan_by_gram_Chr", write_table_by_grammar(wyrcan_df[(wyrcan_df["doc"]=="Chronicle")]))
				write_tex("wyrcan_by_doc", write_table_by_doc(wyrcan_df))
				write_tex("wyrcan_inf_by_doc", write_table_by_doc(wyrcan_df[wyrcan_df["g_kat"]=="inf"]))
				write_tex("wyrcan_prt_by_doc", write_table_by_doc(wyrcan_df[wyrcan_df["g_kat"]=="prt"]))
				write_tex("wyrcan_by_obj", write_table_by_col(wyrcan_df[~(wyrcan_df["g_kat"]=="perf")], "adjunct", non_zero=["ge", "0"]))
				write_tex("wyrcan_by_sem", write_table_by_col(wyrcan_df[~(wyrcan_df["g_kat"]=="perf")], "sem", sort="total"))
				write_tex("wyrcan_bsp_prt_sem_ga", write_example(wyrcan_df[(wyrcan_df["g_kat"]=="prt") & ~(wyrcan_df["sem"].isin(["erschaffen", "bauen", "resultativ"])) & (wyrcan_df["prefix"]=="ge")]))
				write_tex("wyrcan_bsp_prs_rel", write_example(wyrcan_df[(wyrcan_df["clause"].str.contains("relSatz")) & (wyrcan_df["tempus"]=="prs") & ~(wyrcan_df["sem"].isin(["erschaffen", "bauen", "kausativ", "resultativ"]))]))
				write_tex("wyrcan_bsp_prs_rel_ga", write_example(wyrcan_df[(wyrcan_df["clause"].str.contains("relSatz")) & (wyrcan_df["tempus"]=="prs") & (wyrcan_df["prefix"]=="ge") & ~(wyrcan_df["sem"].isin(["erschaffen", "bauen", "kausativ", "resultativ"]))]))
				write_tex("wyrcan_bsp_inf", write_example(wyrcan_df[(wyrcan_df["gram"]=="inf.") & ~(wyrcan_df["sem"].isin(["erschaffen", "bauen", "wirken", "kausativ", "resultativ"]))]))
				write_tex("wyrcan_bsp_arbeiten", write_example(wyrcan_df[(wyrcan_df["sem"].isin(["arbeiten"]))]))
				write_tex("wyrcan_bsp_bauen", write_example(wyrcan_df[(wyrcan_df["sem"].isin(["bauen"]))]))
				write_tex("wyrcan_ein_bsp_bauen_0", write_example(wyrcan_df[(wyrcan_df["sem"].isin(["bauen"])) & (wyrcan_df["g_kat"]=="prt") & (wyrcan_df["prefix"]=="0")].iloc[:1]))
				write_tex("wyrcan_ein_bsp_bauen_inf_ga", write_example(wyrcan_df[(wyrcan_df["sem"].isin(["bauen"])) & (wyrcan_df["g_kat"]=="inf") & (wyrcan_df["prefix"]=="ge")].iloc[:1]))
				write_tex("wyrcan_by_number", write_table_by_col(wyrcan_df[~(wyrcan_df["g_kat"]=="perf")], "number"))
				write_tex("wyrcan_bsp_prt_Or", write_example(wyrcan_df[(wyrcan_df["g_kat"]=="prt") & (wyrcan_df["doc"]=="Orosius")]))
				write_tex("wyrcan_bsp_prt_ga_Or", write_example(wyrcan_df[(wyrcan_df["g_kat"]=="prt") & (wyrcan_df["doc"]=="Orosius") & (wyrcan_df["prefix"]=="ge")]))
				write_tex("wyrcan_bsp_inf_schaffen_0", write_example(wyrcan_df[(wyrcan_df["sem"]=="erschaffen") & (wyrcan_df["prefix"]=="0")]))
				write_tex("wyrcan_ein_bsp_inf_schaffen_0", write_example(wyrcan_df[(wyrcan_df["sem"]=="erschaffen") & (wyrcan_df["prefix"]=="0")].iloc[:1]))
				write_tex("wyrcan_ein_bsp_inf_schaffen_ga", write_example(wyrcan_df[(wyrcan_df["sem"]=="erschaffen") & (wyrcan_df["prefix"]=="ge")].iloc[:1]))
				wyrcan_df_obj = wyrcan_df[(wyrcan_df["object"]=="sub")]
				write_tex("wyrcan_obj_by_gram", write_table_by_grammar(wyrcan_df_obj))
				write_tex("wyrcan_obj_bsp_inf_ga", write_example(wyrcan_df_obj[(wyrcan_df_obj["g_kat"]=="inf") & (wyrcan_df_obj["prefix"]=="ge")]))
				write_tex("wyrcan_obj_bsp_inf_0", write_example(wyrcan_df_obj[(wyrcan_df_obj["g_kat"]=="inf") & (wyrcan_df_obj["prefix"]=="0")]))
				write_tex("wyrcan_obj_bsp_prt_ga", write_example(wyrcan_df_obj[(wyrcan_df_obj["g_kat"]=="prt") & (wyrcan_df_obj["prefix"]=="ge")]))
				write_tex("wyrcan_obj_bsp_prt_0", write_example(wyrcan_df_obj[(wyrcan_df_obj["g_kat"]=="prt") & (wyrcan_df_obj["prefix"]=="0")]))
				wyrcan_df_burg = wyrcan_df[(wyrcan_df["adjunct"]=="burg")]
				write_tex("wyrcan_burg_by_gram", write_table_by_grammar(wyrcan_df_burg))
				write_tex("wyrcan_burg_bsp_prt", write_example(wyrcan_df_burg[wyrcan_df_burg["g_kat"]=="prt"].sort_values("prefix", ascending=False)))
				write_tex("wyrcan_burg_ein_bsp_prt_0", write_example(wyrcan_df_burg[(wyrcan_df_burg["g_kat"]=="prt") & (wyrcan_df_burg["prefix"]=="0")].iloc[:1]))
				write_tex("wyrcan_burg_bsp_prt_ga", write_example(wyrcan_df_burg[(wyrcan_df_burg["g_kat"]=="prt") & (wyrcan_df_burg["prefix"]=="ge")]))
				write_tex("wyrcan_burg_bsp_inf_0", write_example(wyrcan_df_burg[(wyrcan_df_burg["g_kat"]=="inf") & (wyrcan_df_burg["prefix"]=="0")]))
				wyrcan_df_ge = wyrcan_df[(wyrcan_df["adjunct"].isin(["ġesceaft", "ġeweorc"]))]
				write_tex("wyrcan_ge-obj_bsp", write_example(wyrcan_df_ge))
				write_tex("wyrcan_wundor_bsp_0", write_example(wyrcan_df[(wyrcan_df["prefix"]=="0") & (wyrcan_df["adjunct"]=="wundor")], return_number=True))
				
				
				#timbran
				timbran_df = df[df["lemma"]=="timbran"]
				write_tex("timbran_by_gram", write_table_by_grammar(timbran_df))
				write_tex("timbran_bsp_inf_ga", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="ge")]))
				write_tex("timbran_bsp_inf_0", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="0") & ~(timbran_df["rektion"]=="onginnan")]))
				write_tex("timbran_bsp_het_inf_0", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="0") & (timbran_df["rektion"]=="hātan")]))
				write_tex("timbran_bsp_burg_inf_0", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="0") & (timbran_df["adjunct"]=="burg")]))
				write_tex("timbran_bsp_inf_onginnan_0", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="0") & (timbran_df["rektion"]=="onginnan")]))
				write_tex("timbran_ein_bsp_inf_onginnan_0", write_example(timbran_df[(timbran_df["g_kat"]=="inf") & (timbran_df["prefix"]=="0") & (timbran_df["rektion"]=="onginnan")].iloc[:1]))
				write_tex("timbran_bsp_prt_ga", write_example(timbran_df[(timbran_df["g_kat"]=="prt") & (timbran_df["prefix"]=="ge")]))
				write_tex("timbran_ein_bsp_prt_ga", write_example(timbran_df[(timbran_df["g_kat"]=="prt") & (timbran_df["prefix"]=="ge")].iloc[:1]))
				write_tex("timbran_bsp_prt_0", write_example(timbran_df[(timbran_df["g_kat"]=="prt") & (timbran_df["prefix"]=="0")]))
				write_tex("timbran_bsp_prt_rel", write_example(timbran_df[(timbran_df["g_kat"]=="prt") & (timbran_df["clause"]=="relSatz")]))
				
				write_tex("timbran_ongann_count", write_example(timbran_df[timbran_df["rektion"]=="onginnan"], return_number=True))
				
				#strīenan
				strienan_df = df[df["lemma"]=="strīenan"]
				write_tex("strienan_by_gram", write_table_by_grammar(strienan_df))
				
			concrete()
			
			def faktitiv():
				#slēan
				slean_df = df[df["lemma"]=="slēan"]
				ofslean_df = df[df["lemma"]=="ofslēan"]
				write_tex("slean_by_gram", write_table_by_grammar(slean_df))
				write_tex("slean_by_bel", write_table_by_col(slean_df, "belebt"))
				write_tex("ofslean_by_bel", write_table_by_col(ofslean_df, "belebt", prefix="of"))
				
				write_tex("slean_ein_bsp_schlagen_0", write_example(slean_df[(slean_df["sem"]=="schlagen") & (slean_df["doc"]=="Marvels")]))
				write_tex("slean_bsp_schlagen_0", write_example(slean_df[(slean_df["sem"]=="schlagen")]))
				write_tex("slean_bsp_prt_unbel_ga", write_example(slean_df[(slean_df["belebt"]=="unbel") & ~(slean_df["g_kat"]=="perf") & (slean_df["prefix"]=="ge")]))
				write_tex("slean_ein_bsp_unbel_ga", write_example(slean_df[(slean_df["belebt"]=="unbel") & (slean_df["line"].isin([815,])) & (slean_df["prefix"]=="ge")]))
				write_tex("slean_zwei_bsp_unbel_ga", write_example(slean_df[(slean_df["belebt"]=="unbel") & (slean_df["line"].isin([815, 801])) & (slean_df["prefix"]=="ge")]))
				write_tex("slean_bsp_koll_0", write_example(slean_df[(slean_df["sem"]=="kollokation") & (slean_df["prefix"]=="0")]))
				write_tex("slean_bsp_ger", write_example(slean_df[(slean_df["g_kat"]=="ger")]))
				write_tex("ofslean_bsp_bel_prs_rel_0", write_example(ofslean_df[(ofslean_df["adjunct"]=="mann") & (ofslean_df["tempus"]=="prs")]))
				write_tex("slean_bsp_bel_prt_0", write_example(slean_df[(slean_df["belebt"]=="bel") & (slean_df["tempus"]=="prt") & (slean_df["prefix"]=="0")]))
				write_tex("slean_bsp_prt_num", write_example(slean_df[(slean_df["g_kat"]=="prt") & (slean_df["object"]=="num.c.")]))
				write_tex("ofslean_bsp_prt_num", write_example(ofslean_df[(ofslean_df["g_kat"]=="prt") & (ofslean_df["object"]=="num.c.")]))
				write_tex("ofslean_bsp_prt_num_count", write_example(ofslean_df[(ofslean_df["g_kat"]=="prt") & (ofslean_df["object"]=="num.c.")], return_number=True))
				write_tex("slean_bsp_adv", write_example(slean_df[(slean_df["adverb"].isin(["\\textaemacron{}ġþrum ċierre", "flocm\\textaemacron{}lum"]))]))
				write_tex("slean_ein_bsp_adv", write_example(slean_df[(slean_df["adverb_tmp"].isin(["\\textaemacron{}ġþrum ċierre", "flocm\\textaemacron{}lum"])) & (slean_df["line"]==1552)]))
				write_tex("slean_bsp_prt_Or_0", write_example(slean_df[(slean_df["adverb"]=="") & (slean_df["doc"]=="Orosius") & (slean_df["g_kat"]=="prt")]))
				write_tex("slean_bsp_prt_Chr_0", write_example(slean_df[(slean_df["adverb"]=="") & (slean_df["doc"]=="Chronicle") & (slean_df["g_kat"]=="prt") & (slean_df["prefix"]=="0")]))
				write_tex("ofslean_bsp_þy_cyning", write_example(ofslean_df[(ofslean_df["adverb_tmp"]=="þ\\textymacron{}") & (ofslean_df["adjunct"]=="cyning") & (ofslean_df["prefix"]=="of")]))
				write_tex("ofslean_bsp_cyning", write_example(ofslean_df[(ofslean_df["doc"]=="Chronicle") & (ofslean_df["adverb_tmp"]=="") & (ofslean_df["adjunct"]=="cyning") & (ofslean_df["prefix"]=="of")]))
				write_tex("ofslean_bsp_many_men", write_example(ofslean_df[(ofslean_df["year"].isin(["910", "530"]))]))
				write_tex("ofslean_bsp_SVO", write_example(ofslean_df[(ofslean_df["year"].isin(["784"]))]))
				
				write_tex("ofslean_bsp_unbel", write_example(ofslean_df[(ofslean_df["belebt"]=="unbel")]))
				
				#bētan
				betan_df = df[df["lemma"]=="bētan"]
				write_tex("betan_by_gram", write_table_by_grammar(betan_df))
				write_tex("betan_bsp_0", write_example(betan_df[betan_df["prefix"]=="0"]))
				write_tex("betan_bsp_inf_ga", write_example(betan_df[(betan_df["prefix"]=="ge") & (betan_df["g_kat"]=="inf")]))
				
				#trymman
				trymman_df = df[df["lemma"]=="trymman"]
				write_tex("trymman_by_gram", write_table_by_grammar(trymman_df))
				write_tex("trymman_by_doc", write_table_by_doc(trymman_df))
				write_tex("trymman_bsp_prt", write_example(trymman_df[trymman_df["g_kat"]=="prt"]))
				write_tex("trymman_bsp_prt_0", write_example(trymman_df[(trymman_df["g_kat"]=="prt") & (trymman_df["prefix"]=="0")]))
				write_tex("trymman_ein_bsp_prt_ga", write_example(trymman_df[(trymman_df["g_kat"]=="prt") & (trymman_df["prefix"]=="ge") & (trymman_df["line"]==232)]))
				write_tex("trymman_bsp_inf", write_example(trymman_df[trymman_df["g_kat"]=="inf"]))
				write_tex("trymman_bsp_prs", write_example(trymman_df[trymman_df["g_kat"]=="prs"]))
				
				#gladian
				gladian_df = df[df["lemma"]=="gladian"]
				write_tex("gladian_by_gram", write_table_by_grammar(gladian_df))
				write_tex("gladian_by_doc", write_table_by_doc(gladian_df))
				write_tex("gladian_bsp_inf", write_example(gladian_df[(gladian_df["g_kat"]=="inf")].sort_values(["prefix"])))
				write_tex("gladian_bsp_inf_ga", write_example(gladian_df[(gladian_df["g_kat"]=="inf") & ~(gladian_df["adjunct"]=="h\\textaemacron{}lend") & (gladian_df["prefix"]=="ge")]))
				write_tex("gladian_ein_bsp_inf_ga", write_example(gladian_df[(gladian_df["g_kat"]=="inf") & ~(gladian_df["adjunct"]=="h\\textaemacron{}lend") & (gladian_df["prefix"]=="ge")].iloc[:1]))
				write_tex("gladian_bsp_inf_hælend_ga", write_example(gladian_df[(gladian_df["g_kat"]=="inf") & (gladian_df["adjunct"]=="h\\textaemacron{}lend") & (gladian_df["prefix"]=="ge")]))
				write_tex("gladian_bsp_inf_0", write_example(gladian_df[(gladian_df["g_kat"]=="inf") & (gladian_df["prefix"]=="0")]))
				write_tex("gladian_bsp_imp", write_example(gladian_df[(gladian_df["g_kat"]=="imp")]))
				write_tex("gladian_ein_bsp_imp", write_example(gladian_df[(gladian_df["g_kat"]=="imp")].iloc[:1]))
				write_tex("gladian_bsp_prs", write_example(gladian_df[(gladian_df["g_kat"]=="prs")]))
				write_tex("gladian_bsp_prs_ga", write_example(gladian_df[(gladian_df["g_kat"]=="prs") & (gladian_df["prefix"]=="ge")]))
				
				#fæstnian
				fæstnian_df = df[df["lemma"]=="fæstnian"]
				write_tex("fæstnian_by_gram", write_table_by_grammar(fæstnian_df))
				write_tex("fæstnian_bsp_ga", write_example(fæstnian_df[(fæstnian_df["prefix"]=="ge") & ~(fæstnian_df["g_kat"]=="perf")]))
				write_tex("fæstnian_bsp_0", write_example(fæstnian_df[(fæstnian_df["prefix"]=="0") & ~(fæstnian_df["g_kat"]=="perf")]))
				
				#bletsian
				bletsian_df = df[df["lemma"]=="bletsian"]
				write_tex("bletsian_by_gram", write_table_by_grammar(bletsian_df))
				write_tex("bletsian_by_doc", write_table_by_doc(bletsian_df))
				write_tex("bletsian_by_obj", write_table_by_col(bletsian_df[~(bletsian_df["g_kat"]=="perf")], "object"))
				write_tex("bletsian_bsp_prt_ga", write_example(bletsian_df[(bletsian_df["g_kat"]=="prt") & (bletsian_df["prefix"]=="ge")]))
				write_tex("bletsian_ein_bsp_prt_0", write_example(bletsian_df[(bletsian_df["g_kat"]=="prt") & (bletsian_df["prefix"]=="0")].iloc[:1,:]))
				write_tex("bletsian_bsp_inf_ga", write_example(bletsian_df[(bletsian_df["g_kat"]=="inf") & (bletsian_df["prefix"]=="ge")]))
				write_tex("bletsian_bsp_inf_0", write_example(bletsian_df[(bletsian_df["g_kat"]=="inf") & (bletsian_df["prefix"]=="0")]))
				write_tex("bletsian_bsp_inf_prn_0", write_example(bletsian_df[(bletsian_df["g_kat"]=="inf") & (bletsian_df["prefix"]=="0") & ~(bletsian_df["object"]=="sub")]))
				write_tex("bletsian_bsp_prn_ga", write_example(bletsian_df[(bletsian_df["object"]=="prn") & (bletsian_df["prefix"]=="ge") & ~(bletsian_df["g_kat"]=="perf")]))
				write_tex("bletsian_bsp_akk_ga", write_example(bletsian_df[(bletsian_df["object"]=="sub") & (bletsian_df["prefix"]=="ge")]))
				
				#hālgian
				halgian_df = df[df["lemma"]=="hālgian"]
				write_tex("halgian_by_gram", write_table_by_grammar(halgian_df))
				halgian_df = halgian_df[~(halgian_df["g_kat"]=="perf")]
				write_tex("halgian_by_bel", write_table_by_col(halgian_df, "belebt"))
				write_tex("halgian_bsp_prt_husl_ga", write_example(halgian_df[(halgian_df["g_kat"]=="prt") & (halgian_df["adjunct"]=="hūsl") & (halgian_df["prefix"]=="ge")]))
				write_tex("halgian_bsp_prt_husl_0", write_example(halgian_df[(halgian_df["g_kat"]=="prt") & (halgian_df["adjunct"]=="hūsl") & (halgian_df["prefix"]=="0")]))
				write_tex("halgian_bsp_prt_husl_HS", write_example(halgian_df[(halgian_df["g_kat"]=="prt") & (halgian_df["adjunct"]=="hūsl") & (halgian_df["clause"]=="HS")]))
				write_tex("halgian_bsp_prt_husl_temp_0", write_example(halgian_df[(halgian_df["g_kat"]=="prt") & (halgian_df["adjunct"]=="hūsl") & (halgian_df["clause"]=="tempSatz") & (halgian_df["prefix"]=="0")]))
				write_tex("halgian_bsp_prt_husl_temp_ga", write_example(halgian_df[(halgian_df["g_kat"]=="prt") & (halgian_df["adjunct"]=="hūsl") & (halgian_df["clause"]=="tempSatz") & (halgian_df["prefix"]=="ge")]))
				
				#hādian
				hadian_df = df[df["lemma"]=="hādian"]
				write_tex("hadian_by_gram", write_table_by_grammar(hadian_df))
				write_tex("hadian_by_doc", write_table_by_doc(hadian_df[~(hadian_df["g_kat"]=="perf")]))
				write_tex("hadian_bsp_prt_ga", write_example(hadian_df[(hadian_df["g_kat"]=="prt") & (hadian_df["prefix"]=="ge")]))
				write_tex("hadian_bsp_prt_Chr_0", write_example(hadian_df[(hadian_df["g_kat"]=="prt") & (hadian_df["doc"]=="Chronicle") & (hadian_df["prefix"]=="0")]))
				write_tex("hadian_bsp_prt_Lt_0", write_example(hadian_df[(hadian_df["g_kat"]=="prt") & (hadian_df["doc"]=="Letters") & (hadian_df["prefix"]=="0")]))
			faktitiv()
			
			def abstract():
				#endian
				endian_df = df[df["lemma"]=="endian"]
				write_tex("endian_by_gram", write_table_by_grammar(endian_df))
				
				#sēċan
				secan_df = df[df["lemma"]=="sēċan"]
				write_tex("secan_by_gram", write_table_by_grammar(secan_df))
				write_tex("secan_by_doc", write_table_by_doc(secan_df))
				write_tex("secan_bsp_inf_ga", write_example(secan_df[(secan_df["mood"]=="inf") & (secan_df["prefix"]=="ge")]))
				write_tex("secan_bsp_inf_0", write_example(secan_df[(secan_df["mood"]=="inf") & (secan_df["prefix"]=="0")]))
				write_tex("secan_bsp_prs_ga", write_example(secan_df[(secan_df["g_kat"]=="prs") & (secan_df["prefix"]=="ge")]))
				write_tex("secan_bsp_prs_0", write_example(secan_df[(secan_df["g_kat"]=="prs") & (secan_df["prefix"]=="0")]))
				write_tex("secan_bsp_finden", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["adjunct"].isin(["land", "Breten", "Roman", "cyning", "h\\textaemacron{}lend"]))]))
				write_tex("secan_bsp_prt_suchen_unbel", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["sem"]=="suchen") & (secan_df["belebt"]=="unbel")]))
				write_tex("secan_bsp_prt_suchen_bel", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["sem"]=="suchen") & (secan_df["belebt"]=="bel")]))
				write_tex("secan_bsp_prt_land", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["adjunct"]=="land")]))
				write_tex("secan_bsp_prt_aufsuchen_bel_0", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["sem"]=="aufsuchen") & (secan_df["belebt"]=="bel") & (secan_df["prefix"]=="0")]))
				write_tex("secan_bsp_prt_aufsuchen_bel_ga", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["sem"]=="aufsuchen") & (secan_df["belebt"]=="bel") & (secan_df["prefix"]=="ge")]))
				write_tex("secan_bsp_prt_heimsuchen", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["sem"]=="heimsuchen")]))
				write_tex("secan_bsp_here", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["adjunct"]=="here")]))
				write_tex("secan_bsp_hie", write_example(secan_df[(secan_df["g_kat"]=="prt") & (secan_df["adjunct"]=="hīe")]))
				
				#mētan
				metan_df = df[df["lemma"]=="mētan"]
				write_tex("metan_by_gram", write_table_by_grammar(metan_df))
				write_tex("metan_bsp_vorfinden", write_example(metan_df[(metan_df["sem"]=="vorfinden")]))
				
				write_tex("metan_bsp_Or_ga", write_example(metan_df[(metan_df["doc"]=="Orosius") & (metan_df["prefix"]=="ge")]))
				write_tex("metan_bsp_Or_0", write_example(metan_df[(metan_df["doc"]=="Orosius") & ~(metan_df["sem"]=="vorfinden") & (metan_df["prefix"]=="0")]))
				write_tex("metan_bsp_Chr_ga", write_example(metan_df[(metan_df["doc"]=="Chronicle") & (metan_df["prefix"]=="ge")]))
				write_tex("metan_bsp_Chr_0", write_example(metan_df[(metan_df["doc"]=="Chronicle") & ~(metan_df["sem"]=="vorfinden") & (metan_df["prefix"]=="0")]))
				
			abstract()
		write_telic()
		
		def resultative():
			#līcian
			lician_df = df[df["lemma"]=="līcian"]
			write_tex("lician_by_gram", write_table_by_grammar(lician_df))
			write_tex("lician_bsp_prs_ga", write_example(lician_df[(lician_df["g_kat"]=="prs") & (lician_df["prefix"]=="ge")]))
			write_tex("lician_bsp_prs_0", write_example(lician_df[(lician_df["g_kat"]=="prs") & (lician_df["prefix"]=="0")]))
			write_tex("lician_bsp_prt_ga", write_example(lician_df[(lician_df["g_kat"]=="prt")]))
			
			#būgan
			#abstrakte Bedeutung eher als Präteritopräsens?
			bugan_df = df[df["lemma"]=="būgan"]
			write_tex("bugan_by_gram", write_table_by_grammar(bugan_df))
			write_tex("bugan_bsp_Chr", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & (bugan_df["doc"]=="Chronicle")].sort_values("prefix", ascending=False)))
			write_tex("bugan_bsp_Chr_ga", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & (bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="ge")]))
			write_tex("bugan_ein_bsp_Chr_0", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & (bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="0")].iloc[:1]))
			write_tex("bugan_bsp_Aelf_0", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & ~(bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="0")]))
			write_tex("bugan_zwei_bsp_Aelf_0", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & ~(bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="0") & (bugan_df["line"].isin([16, 58]))]))
			write_tex("bugan_bsp_Aelf_ga", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & ~(bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="ge")]))
			write_tex("bugan_zwei_bsp_Aelf_ga", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & ~(bugan_df["doc"]=="Chronicle") & (bugan_df["prefix"]=="ge") & (bugan_df["line"].isin([56, 152, 153]))], condense=True))
			write_tex("bugan_bsp_prt_rel", write_example(bugan_df[(bugan_df["g_kat"]=="prt") & (bugan_df["clause"]=="relSatz")]))
			write_tex("bugan_bsp_perf", write_example(bugan_df[(bugan_df["g_kat"]=="perf")]))
			
			#lǣstan
			laestan_df = df[df["lemma"]=="l\\textaemacron{}stan"]
			write_tex("laestan_by_gram", write_table_by_grammar(laestan_df))
			write_tex("laestan_bsp_inf", write_example(laestan_df[laestan_df["g_kat"]=="inf"]))
			write_tex("laestan_bsp_prs", write_example(laestan_df[laestan_df["g_kat"]=="prs"]))
			write_tex("laestan_bsp_prt", write_example(laestan_df[laestan_df["g_kat"]=="prt"]))
		resultative()
		
		
		##abstrakte? Verben	
		#hātan
		hatan_df = df[df["lemma"]=="hātan"]
		write_tex("hatan_by_gram", write_table_by_grammar(hatan_df))
		hatan_df = hatan_df[~(hatan_df["g_kat"]=="perf")]
		write_tex("hatan_by_sem", write_table_by_col(hatan_df, "sem"))
		write_tex("chi2_hatan_by_sem", chi2(hatan_df, "prefix", "sem"))
		write_tex("hatan_bsp_eac", write_example(hatan_df[hatan_df["adverb"]=="ēac"]))
		write_tex("hatan_bsp_versprechen_ga", write_example(hatan_df[(hatan_df["sem"]=="versprechen") & (hatan_df["prefix"]=="ge")]))
		write_tex("hatan_ein_bsp_versprechen_ga", write_example(hatan_df[(hatan_df["sem"]=="versprechen") & (hatan_df["prefix"]=="ge")].iloc[:1]))
		write_tex("hatan_bsp_befehlen_ga", write_example(hatan_df[(hatan_df["sem"]=="befehlen") & (hatan_df["prefix"]=="ge")]))
		write_tex("hatan_bsp_befehlen_dass_0", write_example(hatan_df[(hatan_df["sem"]=="befehlen") & (hatan_df["object"]=="dassSatz") & (hatan_df["prefix"]=="0")]))
		write_tex("hatan_ein_bsp_befehlen_0", write_example(hatan_df[(hatan_df["sem"]=="befehlen") & (hatan_df["adverb_tmp"]=="æfter+") & (hatan_df["prefix"]=="0")]))
		write_tex("hatan_zwei_bsp_befehlen_0", write_example(hatan_df[(hatan_df["sem"]=="befehlen") & (hatan_df["clause"]=="tempSatz") & (hatan_df["prefix"]=="0")]))
		
		write_tex("hatan_bsp_Or_989", write_example(hatan_df[(hatan_df["doc"]=="Orosius") & (hatan_df["line"]==989)]))
		
		#nemnan
		nemnan_df = df[df["lemma"]=="nemnan"]
		write_tex("nemnan_by_gram", write_table_by_grammar(nemnan_df))
		write_tex("nemnan_by_doc", write_table_by_doc(nemnan_df))
		write_tex("nemnan_bsp_inf", write_example(nemnan_df[nemnan_df["g_kat"]=="inf"]))
		write_tex("nemnan_bsp_prs", write_example(nemnan_df[nemnan_df["g_kat"]=="prs"]))
		write_tex("nemnan_bsp_prt", write_example(nemnan_df[nemnan_df["g_kat"]=="prt"]))
		
		#trūwian
		truwian_df = df[df["lemma"]=="trūwian"]
		write_tex("truwian_by_gram", write_table_by_grammar(truwian_df))
		write_tex("truwian_bsp_0", write_example(truwian_df[(truwian_df["prefix"]=="0") & ~(truwian_df["mood"]=="prc")]))
		write_tex("truwian_bsp_ga", write_example(truwian_df[truwian_df["prefix"]=="ge"]))
		
		
		#fremian ?
		fremian_df = df[df["lemma"]=="fremian"]
		write_tex("fremian_by_gram", write_table_by_grammar(fremian_df))
		write_tex("fremian_by_doc", write_table_by_doc(fremian_df))
		write_tex("fremian_bsp_inf", write_example(fremian_df[fremian_df["g_kat"]=="inf"]))
		write_tex("fremian_bsp_prs", write_example(fremian_df[fremian_df["g_kat"]=="prs"]))
		
		#þingian
		þingian_df = df[df["lemma"]=="þingian"]
		write_tex("þingian_by_gram", write_table_by_grammar(þingian_df))
		write_tex("þingian_bsp_ga_Chron", write_example(þingian_df[(þingian_df["prefix"]=="ge") & (þingian_df["doc"]=="Chronicle")]))
		write_tex("þingian_bsp_ga_Ælf", write_example(þingian_df[(þingian_df["prefix"]=="ge") & ~(þingian_df["doc"]=="Chronicle")]))
		
		#wealdan
		wealdan_df = df[df["lemma"]=="wealdan"]
		write_tex("wealdan_by_gram", write_table_by_grammar(wealdan_df))
		write_tex("wealdan_bsp_inf", write_example(wealdan_df[wealdan_df["g_kat"]=="inf"]))
		write_tex("wealdan_bsp_prt", write_example(wealdan_df[wealdan_df["g_kat"]=="prt"]))
		
		#standan
		standan_df = df[df["lemma"]=="standan"]
		write_tex("standan_by_gram", write_table_by_grammar(standan_df))
		write_tex("standan_bsp_ga", write_example(standan_df[standan_df["prefix"]=="ge"]))
		
		#healdan
		healdan_df = df[df["lemma"]=="healdan"]
		write_tex("healdan_by_gram", write_table_by_grammar(healdan_df))
		write_tex("healdan_by_doc", write_table_by_doc(healdan_df))
		write_tex("healdan_bsp_inf_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["g_kat"]=="inf")]))
		write_tex("healdan_bsp_prs_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["g_kat"]=="prs")]))
		write_tex("healdan_bsp_prt_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["g_kat"]=="prt")]))
		write_tex("healdan_by_sem", write_table_by_col(healdan_df[~(healdan_df["g_kat"]=="perf")], "sem", sort="total"))
		write_tex("healdan_bsp_behalten_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="behalten") & ~(healdan_df["g_kat"]=="perf")]))
		write_tex("healdan_bsp_einhalten_ga", write_example(healdan_df[((healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="einhalten") & ~(healdan_df["g_kat"]=="perf")) | ((healdan_df["line"]==31) & (healdan_df["g_kat"]=="inf"))], condense=True))
		write_tex("healdan_ein_bsp_einhalten_0", write_example(healdan_df[(healdan_df["prefix"]=="0") & (healdan_df["sem"]=="einhalten") & (healdan_df["line"]==101)]))
		write_tex("healdan_bsp_einhalten_inf_0", write_example(healdan_df[(healdan_df["prefix"]=="0") & (healdan_df["sem"]=="einhalten") & (healdan_df["g_kat"]=="inf")]))
		write_tex("healdan_bsp_einhalten_infdat_0", write_example(healdan_df[(healdan_df["prefix"]=="0") & (healdan_df["sem"]=="einhalten") & (healdan_df["gram"]=="inf.dat.")]))
		write_tex("healdan_ein_bsp_einhalten_inf_0", write_example(healdan_df[(healdan_df["prefix"]=="0") & (healdan_df["sem"]=="einhalten") & (healdan_df["g_kat"]=="inf") & (healdan_df["line"]==446)]))
		write_tex("healdan_bsp_bewahren_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="bewahren") & ~(healdan_df["g_kat"]=="perf")]))
		write_tex("healdan_ein_bsp_bewahren_ga", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="bewahren") & ~(healdan_df["g_kat"]=="perf") & (healdan_df["line"]==474)]))
		write_tex("healdan_ein_bsp_bewahren_cristendom", write_example(healdan_df[(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="bewahren") & ~(healdan_df["g_kat"]=="perf") & (healdan_df["line"]==168)]))
		write_tex("healdan_bsp_bewahren_0", write_example(healdan_df[~(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="bewahren") & ~(healdan_df["g_kat"]=="perf")]))
		write_tex("healdan_paar_bsp_bewahren_0", write_example(healdan_df[~(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="bewahren") & ~(healdan_df["g_kat"]=="perf") & (healdan_df["line"].isin([1079, 360]))]))
		write_tex("healdan_bsp_feiern_0", write_example(healdan_df[~(healdan_df["prefix"]=="ge") & (healdan_df["sem"]=="halten") & ~(healdan_df["g_kat"]=="perf")]))
		write_tex("healdan_bsp_cwide", write_example(healdan_df[(healdan_df["adjunct"]=="cwide") & ~(healdan_df["g_kat"]=="perf")]))
		
		#hīersumian
		hiersumian_df = df[df["lemma"]=="hīersumian"]
		write_tex("hiersumian_by_gram", write_table_by_grammar(hiersumian_df))
		write_tex("hiersumian_bsp_inf", write_example(hiersumian_df[(hiersumian_df["g_kat"]=="inf")]))
		write_tex("hiersumian_bsp_prt_ga", write_example(hiersumian_df[(hiersumian_df["g_kat"]=="prt") & (hiersumian_df["prefix"]=="ge")]))
		write_tex("hiersumian_bsp_prt_0", write_example(hiersumian_df[(hiersumian_df["g_kat"]=="prt") & (hiersumian_df["prefix"]=="0")]))
		write_tex("hiersumian_ein_bsp_prt_0", write_example(hiersumian_df[(hiersumian_df["g_kat"]=="prt") & (hiersumian_df["prefix"]=="0")].iloc[:1]))
		
		#wissian/wīsian
		wisian_df = df[df["lemma"].isin(["wīsian", "wissian"])]
		write_tex("wisian_by_gram", write_table_by_grammar(wisian_df))
		write_tex("wisian_by_number", write_table_by_col(wisian_df, "number", sort="reverse"))
		write_tex("wisian_bsp_inf", write_example(wisian_df[(wisian_df["g_kat"]=="inf")]))
		write_tex("wisian_bsp_inf_ga", write_example(wisian_df[(wisian_df["g_kat"]=="inf") & (wisian_df["prefix"]=="ge")]))
		write_tex("wisian_bsp_inf_0", write_example(wisian_df[(wisian_df["g_kat"]=="inf") & (wisian_df["prefix"]=="0")]))
		write_tex("wisian_bsp_prs", write_example(wisian_df[(wisian_df["g_kat"]=="prs")]))
		write_tex("wisian_bsp_prs_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prs") & (wisian_df["prefix"]=="ge")]))
		write_tex("wisian_paar_bsp_prs_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prs") & (wisian_df["prefix"]=="ge") & (wisian_df["line"].isin([173, 434, 499]))]))
		write_tex("wisian_ein_bsp_prs_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prs") & (wisian_df["prefix"]=="ge") & (wisian_df["line"].isin([173]))]))
		write_tex("wisian_zwei_bsp_prs_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prs") & (wisian_df["prefix"]=="ge") & (wisian_df["line"].isin([434, 499]))]))
		write_tex("wisian_bsp_prs_0", write_example(wisian_df[(wisian_df["g_kat"]=="prs") & (wisian_df["prefix"]=="0")]))
		write_tex("wisian_bsp_prt", write_example(wisian_df[(wisian_df["g_kat"]=="prt")]))
		write_tex("wisian_ein_bsp_prt_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prt") & (wisian_df["prefix"]=="ge")].iloc[:1]))
		write_tex("wisian_bsp_prt_ga", write_example(wisian_df[(wisian_df["g_kat"]=="prt") & (wisian_df["prefix"]=="ge")]))
		write_tex("wisian_bsp_prt_0", write_example(wisian_df[(wisian_df["g_kat"]=="prt") & (wisian_df["prefix"]=="0")]))
		
		#tēon
		teon_df = df[df["lemma"]=="tēon"]
		write_tex("teon_by_gram", write_table_by_grammar(teon_df))
		write_tex("teon_by_bel", write_table_by_col(teon_df[~(teon_df["g_kat"]=="perf")], "belebt"))
		write_tex("teon_bsp_inf", write_example(teon_df[teon_df["g_kat"]=="inf"]))
		write_tex("teon_bsp_prt_ga", write_example(teon_df[(teon_df["g_kat"]=="prt") & (teon_df["prefix"]=="ge")]))
		write_tex("teon_bsp_prt_0", write_example(teon_df[(teon_df["g_kat"]=="prt") & (teon_df["prefix"]=="ge")]))
		write_tex("teon_bsp_prt_to", write_example(teon_df[(teon_df["g_kat"]=="prt") & (teon_df["pr_obj"]=="tō+")]))
		
		##Verben des Sagens
		def inhaltsverben():
			inhalt_df = df[(df["sem"]=="inhalt") & ~(df["status"]=="sem")]
			write_tex("inhalt_by_gram", write_table_by_grammar(inhalt_df))
			write_tex("inhalt_by_lemma", write_table_by_col(inhalt_df, "lemma", sort="percentage"))
			inhalt_df = inhalt_df[~(inhalt_df["g_kat"]=="perf")]
			write_tex("inhalt_bsp_ga", write_example(inhalt_df[(inhalt_df["prefix"]=="ge") & ~(inhalt_df["mood"]=="prc") & ~(inhalt_df["g_kat"]=="perf")].sort_values(["lemma"])))
			write_tex("inhalt_by_obj", write_table_by_col(inhalt_df[~(inhalt_df["object"]=="")], "object"))
			
			#secgan
			secgan_df = df[(df["lemma"]=="seċġan")]
			write_tex("secgan_by_gram", write_table_by_grammar(secgan_df))
			secgan_df = secgan_df[~(secgan_df["g_kat"]=="perf")]
			write_tex("secgan_by_doc", write_table_by_doc(secgan_df))
			write_tex("secgan_bsp_prs_ga", write_example(secgan_df[(secgan_df["g_kat"]=="prs") & (secgan_df["prefix"]=="ge")]))
			write_tex("secgan_bsp_prs_daed_0", write_example(secgan_df[(secgan_df["adjunct"]=="d\\textaemacron{}d") & (secgan_df["prefix"]=="0")]))
			write_tex("secgan_bsp_inf_ga", write_example(secgan_df[(secgan_df["gram"]=="inf.") & (secgan_df["prefix"]=="ge")]))
			write_tex("secgan_bsp_inf_dass_0", write_example(secgan_df[(secgan_df["gram"]=="inf.") & (secgan_df["adjunct"]=="þæt") & (secgan_df["prefix"]=="0")]))
			write_tex("secgan_bsp_infdat_ga", write_example(secgan_df[(secgan_df["gram"]=="inf.dat.") & (secgan_df["prefix"]=="ge")]))
			write_tex("secgan_bsp_infdat_0", write_example(secgan_df[(secgan_df["gram"]=="inf.dat.") & (secgan_df["prefix"]=="0")]))
			write_tex("secgan_bsp_1sg_akk_0", write_example(secgan_df[(secgan_df["obj_case"]=="akk") & (secgan_df["gram"].str.contains("1.sg.(?:cnj|ind).prs.")) & (secgan_df["prefix"]=="0")]))
			
			write_tex("secgan_by_obj", write_table_by_col(secgan_df, "object"))
			write_tex("secgan_by_obj_Or", write_table_by_col(secgan_df[(secgan_df["doc"]=="Orosius")], "object"))
			write_tex("secgan_bsp_prt_akk_Or_0", write_example(secgan_df[(secgan_df["obj_case"]=="akk") & (secgan_df["doc"]=="Orosius") & (secgan_df["prefix"]=="0") & (secgan_df["tempus"]=="prt")]))
			write_tex("secgan_bsp_inf_Or_0", write_example(secgan_df[(secgan_df["gram"]=="inf.") & (secgan_df["doc"]=="Orosius") & (secgan_df["prefix"]=="0")]))
			write_tex("secgan_bsp_infdat_Or_0", write_example(secgan_df[(secgan_df["gram"]=="inf.dat.") & (secgan_df["doc"]=="Orosius") & (secgan_df["prefix"]=="0") & (secgan_df["adverb"]=="unġelīefedlīċ")]))
				 
			#cweþan
			cweþan_df = df[df["lemma"]=="cweþan"]
			write_tex("cweþan_by_gram", write_table_by_grammar(cweþan_df))
			write_tex("cweþan_by_doc", write_table_by_doc(cweþan_df))
			write_tex("cweþan_prt_by_clause", write_table_by_col(cweþan_df[(cweþan_df["g_kat"]=="prt")], "clause"))
			write_tex("cweþan_prt_by_obj", write_table_by_col(cweþan_df[(cweþan_df["g_kat"]=="prt")], "object"))
			write_tex("cweþan_bsp_prs_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prs") & (cweþan_df["prefix"]=="ge")]))
			write_tex("cweþan_zwei_bsp_prs_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prs") & (cweþan_df["prefix"]=="ge") & (cweþan_df["line"].isin([126, 153]))]))
			write_tex("cweþan_bsp_prs_rel_0", write_example(cweþan_df[(cweþan_df["g_kat"]=="prs") & (cweþan_df["clause"].str.contains("relSatz")) & (cweþan_df["prefix"]=="0")]))
			write_tex("cweþan_bsp_prt_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["prefix"]=="ge")]))
			write_tex("cweþan_bsp_prt_rel_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"].str.contains("relSatz")) & (cweþan_df["prefix"]=="ge")]))
			write_tex("cweþan_zwei_bsp_prt_rel_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"].str.contains("relSatz")) & (cweþan_df["prefix"]=="ge") & (cweþan_df["line"].isin([657, 105]))]))
			write_tex("cweþan_bsp_prt_rel_0", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"].str.contains("relSatz")) & (cweþan_df["object"]=="prn") & (cweþan_df["prefix"]=="0")]))
			write_tex("cweþan_zwei_bsp_prt_rel_0", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"].str.contains("relSatz")) & (cweþan_df["object"]=="prn") & (cweþan_df["prefix"]=="0") & (cweþan_df["line"].isin([405, 7]))]))
			write_tex("cweþan_bsp_prt_temp_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"]=="tempSatz") & (cweþan_df["prefix"]=="ge")]))
			write_tex("cweþan_bsp_prt_temp_0", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"]=="tempSatz") & (cweþan_df["prefix"]=="0")]))
			write_tex("cweþan_bsp_prt_HS_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"]=="HS") & (cweþan_df["prefix"]=="ge")]))
			write_tex("cweþan_zwei_bsp_prt_HS_ga", write_example(cweþan_df[(cweþan_df["g_kat"]=="prt") & (cweþan_df["clause"]=="HS") & (cweþan_df["prefix"]=="ge") & (cweþan_df["line"].isin([171, 901]))]))
			
			write_tex("cweþan_bsp_obj_0", write_example(cweþan_df[((cweþan_df["object"].isin(["sub", "prn"])) & ~(cweþan_df["adjunct"]=="latein")) & ~((cweþan_df["g_kat"]=="prs") & (cweþan_df["prefix"]=="ge"))]))
			write_tex("cweþan_bsp_word_ga", write_example(cweþan_df[(cweþan_df["adjunct"]==("word")) & ((cweþan_df["prefix"]=="ge"))]))
			
			#andwyrdan
			andwyrdan_df = inhalt_df[inhalt_df["lemma"]=="andwyrdan"]
			write_tex("andwyrdan_by_gram", write_table_by_grammar(andwyrdan_df))
			write_tex("andwyrdan_by_doc", write_table_by_doc(andwyrdan_df))
			write_tex("andwyrdan_by_obj", write_table_by_col(andwyrdan_df, "object"))
			write_tex("andwyrdan_bsp_ga", write_example(andwyrdan_df[andwyrdan_df["prefix"]=="ge"]))
			write_tex("andwyrdan_bsp_intr_0", write_example(andwyrdan_df[(andwyrdan_df["object"]=="0") & (andwyrdan_df["prefix"]=="0")]))
			write_tex("andwyrdan_ein_bsp_intr_0", write_example(andwyrdan_df[(andwyrdan_df["object"]=="0") & (andwyrdan_df["prefix"]=="0")].iloc[:1]))
			
			#sprecan
			sprecan_df = df[df["lemma"]=="sprecan"]
			write_tex("sprecan_by_gram", write_table_by_grammar(sprecan_df))
			write_tex("sprecan_by_doc", write_table_by_doc(sprecan_df))
			write_tex("sprecan_bsp_prt_ga", write_example(sprecan_df[(sprecan_df["g_kat"]=="prt") & (sprecan_df["prefix"]=="ge")]))
			write_tex("sprecan_bsp_perf_ga", write_example(sprecan_df[(sprecan_df["g_kat"]=="perf") & (sprecan_df["prefix"]=="ge")]))
			write_tex("sprecan_akk_by_bel", write_table_by_col(sprecan_df[(sprecan_df["obj_case"]=="akk")], "belebt"))
			write_tex("sprecan_bsp_akk_0", write_example(sprecan_df[(sprecan_df["obj_case"]=="akk") & (sprecan_df["prefix"]=="0")]))
			
			#reċċan
			reccan_df = df[df["lemma"]=="reċċan"]
			write_tex("reccan_by_gram", write_table_by_grammar(reccan_df))
			write_tex("reccan_by_doc", write_table_by_doc(reccan_df))
			write_tex("reccan_bsp_ga", write_example(reccan_df[(reccan_df["prefix"]=="ge") & ~(reccan_df["g_kat"]=="perf")]))
			write_tex("reccan_bsp_prs_0", write_example(reccan_df[(reccan_df["prefix"]=="0") & (reccan_df["g_kat"]=="prs")]))
			write_tex("reccan_ein_bsp_prs_0", write_example(reccan_df[(reccan_df["prefix"]=="0") & (reccan_df["g_kat"]=="prs")].iloc[:1]))
			write_tex("reccan_bsp_prt_0", write_example(reccan_df[(reccan_df["prefix"]=="0") & (reccan_df["g_kat"]=="prt")]))
			
			#singan
			singan_df = df[df["lemma"]=="singan"]
			write_tex("singan_by_gram", write_table_by_grammar(singan_df))
			write_tex("singan_by_doc", write_table_by_doc(singan_df))
			write_tex("singan_perf_by_doc", write_table_by_doc(singan_df[singan_df["g_kat"]=="perf"]))
			singan_df = singan_df[~(singan_df["g_kat"]=="perf")]
			write_tex("singan_by_obj", write_table_by_col(singan_df, "obj_case"))
			write_tex("singan_bsp_prt_ga", write_example(singan_df[(singan_df["tempus"]=="prt") & (singan_df["prefix"]=="ge")]))
			write_tex("singan_bsp_prt_HS_0", write_example(singan_df[(singan_df["tempus"]=="prt") & (singan_df["clause"]=="HS") & (singan_df["prefix"]=="0")]))
			write_tex("singan_bsp_prt_rel_0", write_example(singan_df[(singan_df["tempus"]=="prt") & (singan_df["clause"].isin(["relSatz", "app"])) & (singan_df["prefix"]=="0")]))
			write_tex("singan_bsp_prs_ga", write_example(singan_df[(singan_df["tempus"]=="prs") & (singan_df["prefix"]=="ge")]))
			
			write_tex("singan_bsp_seofon_sangas_0", write_example(singan_df[(singan_df["context"].str.contains("seofon")) & (singan_df["prefix"]=="0")]))
			write_tex("singan_bsp_ælc_0", write_example(singan_df[(singan_df["context"].str.contains("ælc")) & (singan_df["prefix"]=="0")]))
			write_tex("singan_bsp_prn", write_example(singan_df[(singan_df["object"]=="prn")].sort_values("tempus")))
			
			write_tex("singan_bsp_Wulfstan2", write_example(singan_df[~(singan_df["g_kat"]=="perf") & (singan_df["page"]=="To Wulfstan (2)")].sort_values("line"), condense=True))
			write_tex("singan_drei_bsp_Wulfstan2", write_example(singan_df[~(singan_df["g_kat"]=="perf") & (singan_df["page"]=="To Wulfstan (2)")].sort_values("line"), condense=True, howmany=3))
			write_tex("singan_bsp_Wulfstan2_count", write_example(singan_df[~(singan_df["g_kat"]=="perf") & (singan_df["page"]=="To Wulfstan (2)")], return_number=True))
			write_tex("singan_bsp_Wulfsige_0", write_example(singan_df[(singan_df["prefix"]=="0") & (singan_df["page"]=="To Wulfsige")], condense=True))
			write_tex("singan_bsp_Sigeweard_0", write_example(singan_df[(singan_df["prefix"]=="0") & (singan_df["page"]=="To Sigeweard")]))
			
			#clipian
			clipian_df = df[df["lemma"]=="clipian"]
			write_tex("clipian_by_gram", write_table_by_grammar(clipian_df))
			write_tex("clipian_by_doc", write_table_by_doc(clipian_df))
			write_tex("clipian_bsp_ga", write_example(clipian_df[(clipian_df["prefix"]=="ge")]))
			write_tex("clipian_bsp_akk_0", write_example(clipian_df[(clipian_df["obj_case"]=="akk") & (clipian_df["prefix"]=="0")]))
			
			#leornian
			leornian_df = df[df["lemma"]=="leornian"]
			write_tex("leornian_by_gram", write_table_by_grammar(leornian_df))
			write_tex("leornian_bsp_prt", write_example(leornian_df[leornian_df["tempus"]=="prt"]))
			write_tex("leornian_bsp_inf", write_example(leornian_df[leornian_df["g_kat"]=="inf"]))
			write_tex("leornian_ein_bsp_inf", write_example(leornian_df[leornian_df["g_kat"]=="inf"].iloc[:1]))
			write_tex("leornian_bsp_prt_ga", write_example(leornian_df[(leornian_df["tempus"]=="prt") & (leornian_df["prefix"]=="ge")]))
			write_tex("leornian_paar_bsp_prt_0", write_example(leornian_df[(leornian_df["tempus"]=="prt") & (leornian_df["prefix"]=="0") & (leornian_df["line"].isin([732]))]))
			
			#tǣċan
			tæcan_df = df[df["lemma"]=="t\\textaemacron{}ċan"]
			write_tex("tæcan_by_gram", write_table_by_grammar(tæcan_df))
			write_tex("tæcan_bsp_inf_ga", write_example(tæcan_df[(tæcan_df["g_kat"]=="inf") & (tæcan_df["prefix"]=="ge")]))
			write_tex("tæcan_bsp_inf_0", write_example(tæcan_df[(tæcan_df["g_kat"]=="inf") & (tæcan_df["prefix"]=="0")]))
			write_tex("tæcan_bsp_prt_ga", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["prefix"]=="ge")]))
			write_tex("tæcan_bsp_prt_þeaw_ga", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["adjunct"]=="þēaw") & (tæcan_df["prefix"]=="ge")]))
			write_tex("tæcan_bsp_prt_swa_ga", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["conjunction"]=="swā") & (tæcan_df["prefix"]=="ge")]))
			write_tex("tæcan_bsp_prt_dass_ga", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["object"]=="dassSatz") & (tæcan_df["prefix"]=="ge")]))
			write_tex("tæcan_bsp_prt_swa_0", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["conjunction"]=="swā") & (tæcan_df["prefix"]=="0")]))
			write_tex("tæcan_bsp_prt_dass_0", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["object"]=="dassSatz") & (tæcan_df["prefix"]=="0")]))
			write_tex("tæcan_bsp_prt_akk_HS_0", write_example(tæcan_df[(tæcan_df["g_kat"]=="prt") & (tæcan_df["obj_case"]=="akk") & (tæcan_df["clause"]=="HS") & (tæcan_df["prefix"]=="0")]))
			
			write_tex("tæcan_bsp_bestimmen_0", write_example(tæcan_df[(tæcan_df["sem"]=="festsetzen") & (tæcan_df["prefix"]=="0")]))
			
			#āscian
			ascian_df = df[df["lemma"]=="āscian"]
			write_tex("ascian_by_gram", write_table_by_grammar(ascian_df))
			write_tex("ascian_ein_bsp_ga", write_example(ascian_df[(ascian_df["prefix"]=="ge") & (ascian_df["page"]=="2.02,04")].iloc[0:1,:]))
			write_tex("ascian_ein_bsp_0", write_example(ascian_df[ascian_df["prefix"]=="0"].iloc[0:1,:]))
			
			#bodian
			bodian_df = df[df["lemma"]=="bodian"]
			write_tex("bodian_by_gram", write_table_by_grammar(bodian_df))
			write_tex("bodian_by_doc", write_table_by_doc(bodian_df))
			write_tex("bodian_bsp_prt_ga", write_example(bodian_df[(bodian_df["g_kat"]=="prt") & (bodian_df["prefix"]=="ge")]))
			write_tex("bodian_ein_bsp_prt_0", write_example(bodian_df[(bodian_df["g_kat"]=="prt") & (bodian_df["prefix"]=="0") & (bodian_df["line"]==151)]))
			
			#cȳþan
			cyþan_df = df[df["lemma"]=="c\\textymacron{}þan"]
			write_tex("cyþan_by_gram", write_table_by_grammar(cyþan_df))
			write_tex("cyþan_by_doc", write_table_by_doc(cyþan_df))
			write_tex("cyþan_bsp_inf_ga", write_example(cyþan_df[(cyþan_df["g_kat"]=="inf") & (cyþan_df["prefix"]=="ge")]))
			write_tex("cyþan_bsp_inf_0", write_example(cyþan_df[(cyþan_df["g_kat"]=="inf") & (cyþan_df["prefix"]=="0")]))
			write_tex("cyþan_zwei_bsp_inf_0", write_example(cyþan_df[(cyþan_df["g_kat"]=="inf") & (cyþan_df["prefix"]=="0") & (cyþan_df["line"].isin([104, 950]))]))
			write_tex("cyþan_bsp_dass_0", write_example(cyþan_df[(cyþan_df["object"]=="dassSatz") & (cyþan_df["prefix"]=="0")]))
			
			#bīecnian
			biecnian_df = df[df["lemma"]=="bīecnian"]
			write_tex("biecnian_by_gram", write_table_by_grammar(biecnian_df))
			write_tex("biecnian_bsp_ga", write_example(biecnian_df[(biecnian_df["prefix"]=="ge") & ~(biecnian_df["g_kat"]=="perf")]))
			write_tex("biecnian_bsp_0", write_example(biecnian_df[(biecnian_df["prefix"]=="0") & ~(biecnian_df["g_kat"]=="perf")]))
			
			#þafian
			þafian_df = df[df["lemma"]=="þafian"]
			write_tex("þafian_by_gram", write_table_by_grammar(þafian_df))
			write_tex("þafian_bsp_0", write_example(þafian_df[þafian_df["prefix"]=="0"]))
			
			#swerian
			swerian_df = df[df["lemma"]=="swerian"]
			write_tex("swerian_by_gram", write_table_by_grammar(swerian_df))
			write_tex("swerian_bsp_prt_ga", write_example(swerian_df[(swerian_df["prefix"]=="ge") & (swerian_df["g_kat"]=="prt")]))
			write_tex("swerian_bsp_prt_aþ_0", write_example(swerian_df[(swerian_df["prefix"]=="0") & (swerian_df["adjunct"]=="āþ") & (swerian_df["g_kat"]=="prt")]))
			write_tex("swerian_bsp_dass_akk_0", write_example(swerian_df[(swerian_df["prefix"]=="0") & (swerian_df["obj_case"]=="akk") & (swerian_df["object"]=="dassSatz")]))
			
			#wearnian
			wearnian_df = df[df["lemma"]=="wearnian"]
			write_tex("wearnian_by_gram", write_table_by_grammar(wearnian_df))
			write_tex("wearnian_bsp_mod", write_example(wearnian_df[(wearnian_df["mood"].isin(["imp", "cnj"]))]))
			write_tex("wearnian_bsp_prt", write_example(wearnian_df[(wearnian_df["g_kat"]=="prt")]))
			write_tex("wearnian_bsp_prs_ga", write_example(wearnian_df[(wearnian_df["g_kat"]=="prs") & (wearnian_df["prefix"]=="ge")]))
			
			#andettan
			andettan_df = df[df["lemma"]=="andettan"]
			write_tex("andettan_bsp", write_example(andettan_df))
			
			#witan
			witan_df = df[df["lemma"]=="witan"]
			write_tex("witan_by_gram", write_table_by_grammar(witan_df))
			write_tex("witan_bsp_ga", write_example(witan_df[(witan_df["prefix"]=="ge")]))
			write_tex("witan_bsp_mod_dass_0", write_example(witan_df[(witan_df["mood"].isin(["cnj", "imp"])) & (witan_df["object"]=="dassSatz") & (witan_df["prefix"]=="0")]))
			
			#þenċan
			þencan_df = df[df["lemma"]=="þenċan"]
			write_tex("þencan_by_gram", write_table_by_grammar(þencan_df))
			write_tex("þencan_bsp_ga", write_example(þencan_df[(þencan_df["prefix"]=="ge")]))
			write_tex("þencan_bsp_prs_0", write_example(þencan_df[(þencan_df["g_kat"]=="prs") & (þencan_df["prefix"]=="0")]))
			
			#þynċan
			þyncan_df = df[df["lemma"]=="þynċan"]
			write_tex("þyncan_by_gram", write_table_by_grammar(þyncan_df))
			write_tex("þyncan_bsp_ga", write_example(þyncan_df[~(þyncan_df["g_kat"]=="perf") & (þyncan_df["prefix"]=="ge")]))
			write_tex("þyncan_bsp_prt_dass_0", write_example(þyncan_df[(þyncan_df["g_kat"]=="prt") & (þyncan_df["object"]=="dassSatz") & (þyncan_df["obj_case"]=="") & (þyncan_df["prefix"]=="0")]))
			
			#mǣnan
			mænan_df = df[df["lemma"]=="m\\textaemacron{}nan"]
			write_tex("mænan_by_gram", write_table_by_grammar(mænan_df))
			write_tex("mænan_by_doc", write_table_by_doc(mænan_df))
			write_tex("mænan_bsp_ga", write_example(mænan_df[(mænan_df["prefix"]=="ge") & ~(mænan_df["g_kat"]=="perf")]))
			write_tex("mænan_bsp_0", write_example(mænan_df[(mænan_df["prefix"]=="0") & ~(mænan_df["g_kat"]=="perf")]))
		
			#cunnan
			cunnan_df = df[df["lemma"]=="cunnan"]
			write_tex("cunnan_by_gram", write_table_by_grammar(cunnan_df))
			write_tex("cunnan_bsp_prt_ga", write_example(cunnan_df[(cunnan_df["g_kat"]=="prt") & (cunnan_df["prefix"]=="ge")]))
			write_tex("cunnan_bsp_prt_0", write_example(cunnan_df[(cunnan_df["g_kat"]=="prt") & (cunnan_df["sem"]=="kennen") & (cunnan_df["prefix"]=="0")]))
			
			#bȳsnian
			bysnian_df = df[df["lemma"]=="b\\textymacron{}snian"]
			write_tex("bysnian_by_gram", write_table_by_grammar(bysnian_df))
			write_tex("bysnian_bsp_ga", write_example(bysnian_df[(bysnian_df["prefix"]=="ge") & ~(bysnian_df["g_kat"]=="perf")]))
			write_tex("bysnian_bsp_0", write_example(bysnian_df[(bysnian_df["prefix"]=="0") & ~(bysnian_df["g_kat"]=="perf")]))
		inhaltsverben()
		
		##kognitive Verben
		def wahrnehmungsverben():
			#sēon s.o.
			
			#hīeran
			hieran_df = df[(df["lemma"]=="hīeran")]
			write_tex("hieran_by_gram", write_table_by_grammar(hieran_df))
			write_tex("hieran_by_doc", write_table_by_doc(hieran_df))
			hieran_df = hieran_df[~(hieran_df["g_kat"]=="perf")]
			write_tex("hieran_by_sem", write_table_by_col(hieran_df, "sem"))
			write_tex("hieran_bsp_infdat", write_example(hieran_df[(hieran_df["gram"]=="inf.dat.")]))
			write_tex("hieran_bsp_prt_akk_ga", write_example(hieran_df[(hieran_df["g_kat"]=="prt") & (hieran_df["obj_case"]=="akk") & (hieran_df["prefix"]=="ge")]))
			write_tex("hieran_infdat_count", write_example(hieran_df[hieran_df["gram"]=="inf.dat."], return_number=True))
			write_tex("hieran_bsp_aci", write_example(hieran_df[(hieran_df["object"]=="AcI")]))
			
			write_tex("hieran_bsp_Chr_gehören", write_example(hieran_df[(hieran_df["doc"]=="Chronicle") & (hieran_df["sem"]=="gehören")]))
			write_tex("hieran_ein_bsp_Chr_gehören", write_example(hieran_df[(hieran_df["doc"]=="Chronicle") & (hieran_df["sem"]=="gehören")].iloc[:1]))
			write_tex("hieran_bsp_Chr_hören_ga", write_example(hieran_df[(hieran_df["doc"]=="Chronicle") & (hieran_df["sem"]=="kognitiv") & (hieran_df["prefix"]=="ge")]))
			write_tex("hieran_bsp_Chr_hören_0", write_example(hieran_df[(hieran_df["doc"]=="Chronicle") & (hieran_df["sem"]=="kognitiv") & (hieran_df["prefix"]=="0")]))
			write_tex("hieran_ein_bsp_Chr_hören_0", write_example(hieran_df[(hieran_df["doc"]=="Chronicle") & (hieran_df["sem"]=="kognitiv") & (hieran_df["prefix"]=="0") & (hieran_df["line"]==1228)]))
			write_tex("hieran_ein_bsp_Or_hören_ga", write_example(hieran_df[(hieran_df["doc"]=="Orosius") & (hieran_df["sem"]=="kognitiv") & (hieran_df["prefix"]=="ge")].iloc[:1]))
			write_tex("hieran_bsp_Aelf_0", write_example(hieran_df[(hieran_df["doc"].isin(["Catholic Homilies", "Prefaces", "Letters"])) & (hieran_df["prefix"]=="0")]))
			write_tex("hieran_bsp_Aelf_mod_ga", write_example(hieran_df[(hieran_df["doc"].isin(["Catholic Homilies", "Prefaces", "Letters"])) & (hieran_df["clause"].isin(["kondSatz", "dassSatz"])) &  (hieran_df["prefix"]=="ge")]))
			write_tex("hieran_bsp_Aelf_gehören", write_example(hieran_df[(hieran_df["doc"].isin(["Catholic Homilies", "Prefaces", "Letters"])) & (hieran_df["sem"]=="gehören")]))
			write_tex("hieran_bsp_Aelf_hören", write_example(hieran_df[(hieran_df["doc"].isin(["Catholic Homilies", "Prefaces", "Letters"])) & (hieran_df["sem"]=="kognitiv")]))
			write_tex("hieran_ein_bsp_Aelf_hören", write_example(hieran_df[(hieran_df["doc"].isin(["Catholic Homilies", "Prefaces", "Letters"])) & (hieran_df["sem"]=="kognitiv")].iloc[:1]))
			
			#scēawian
			sceawian_df = df[df["lemma"]=="scēawian"]
			write_tex("sceawian_by_gram", write_table_by_grammar(sceawian_df))
			write_tex("sceawian_bsp_prs_ga", write_example(sceawian_df[(sceawian_df["g_kat"]=="prs") & (sceawian_df["prefix"]=="ge")]))
			write_tex("sceawian_bsp_prs_0", write_example(sceawian_df[(sceawian_df["g_kat"]=="prs") & (sceawian_df["prefix"]=="0")]))
			write_tex("sceawian_bsp_prt_ga", write_example(sceawian_df[(sceawian_df["g_kat"]=="prt") & (sceawian_df["prefix"]=="ge")]))
			write_tex("sceawian_bsp_prt_0", write_example(sceawian_df[(sceawian_df["g_kat"]=="prt") & (sceawian_df["prefix"]=="0")]))
			
			#rǣdan
			rædan_df = df[df["lemma"]=="r\\textaemacron{}dan"]
			write_tex("rædan_by_gram", write_table_by_grammar(rædan_df))
			write_tex("rædan_bsp_ga", write_example(rædan_df[(rædan_df["prefix"]=="ge")]))
		wahrnehmungsverben()
		
		###telische verben
		##abstrakt
		#weorþan
		weorþan_df = df[df["lemma"]=="weorþan"]
		write_tex("weorþan_by_gram", write_table_by_grammar(weorþan_df))
		write_tex("weorþan_bsp_inf", write_example(weorþan_df[weorþan_df["g_kat"]=="inf"]))
		write_tex("weorþan_bsp_prs", write_example(weorþan_df[weorþan_df["g_kat"]=="prs"]))
		write_tex("weorþan_bsp_prt_ga", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["prefix"]=="ge")]))
		write_tex("weorþan_bsp_prt_0", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["prefix"]=="0")].iloc[:8,:]))
		write_tex("weorþan_by_sem", write_table_by_col(weorþan_df[(weorþan_df["g_kat"]=="prt")], "sem"))
		write_tex("weorþan_bsp_geschehen_ga", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["sem"]=="geschehen") & (weorþan_df["prefix"]=="ge")]))
		write_tex("weorþan_bsp_geschehen_0", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["sem"]=="geschehen") & (weorþan_df["prefix"]=="0")]))
		write_tex("weorþan_bsp_leer", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["sem"].isin(["0", "?"]))]))
		write_tex("weorþan_bsp_sein", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["sem"]=="sein")]))
		write_tex("weorþan_bsp_werden", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["sem"]=="werden")]))
		write_tex("weorþan_bsp_hunger", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["adjunct"]=="hunger")]))
		write_tex("weorþan_bsp_wundor", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["adjunct"]=="wundor")]))
		write_tex("weorþan_bsp_dass", write_example(weorþan_df[(weorþan_df["g_kat"]=="prt") & (weorþan_df["object"]=="dassSatz")]))
		
		#ċēosan
		ceosan_df = df[df["lemma"]=="ċēosan"]
		write_tex("ceosan_by_gram", write_table_by_grammar(ceosan_df))
		write_tex("ceosan_bsp_0", write_example(ceosan_df[ceosan_df["prefix"]=="0"]))
		write_tex("ceosan_bsp_pl_ga", write_example(ceosan_df[(ceosan_df["prefix"]=="ge") & (ceosan_df["number"]=="pl") & ~(ceosan_df["g_kat"]=="perf")]))
		write_tex("ceosan_bsp_ne_ga", write_example(ceosan_df[(ceosan_df["prefix"]=="ge") & ~ (ceosan_df["negation"]=="0") & ~(ceosan_df["g_kat"]=="perf")]))
		
		#unnan
		unnan_df = df[df["lemma"]=="unnan"]
		write_tex("unnan_by_gram", write_table_by_grammar(unnan_df))
		write_tex("unnan_by_doc", write_table_by_doc(unnan_df))
		write_tex("unnan_bsp_prt", write_example(unnan_df[unnan_df["g_kat"]=="prt"]))
		write_tex("unnan_bsp_prs", write_example(unnan_df[unnan_df["g_kat"]=="prs"]))
		
		
		#fullian
		fullian_df = df[df["lemma"]=="fullian"]
		write_tex("fullian_by_gram", write_table_by_grammar(fullian_df))
		write_tex("fullian_bsp_cnj", write_example(fullian_df[(fullian_df["g_kat"]=="prs") & (fullian_df["mood"]=="cnj")]))
		write_tex("fullian_bsp_ind", write_example(fullian_df[(fullian_df["g_kat"]=="prs") & (fullian_df["mood"]=="ind")]))
		
		
		#laþian
		laþian_df = df[df["lemma"]=="laþian"]
		write_tex("laþian_by_gram", write_table_by_grammar(laþian_df))
		write_tex("laþian_bsp_inf_ga", write_example(laþian_df[(laþian_df["g_kat"]=="inf") & (laþian_df["prefix"]=="ge")]))
		write_tex("laþian_bsp_inf_0", write_example(laþian_df[(laþian_df["g_kat"]=="inf") & (laþian_df["prefix"]=="0")]))
		write_tex("laþian_bsp_prs_0", write_example(laþian_df[(laþian_df["g_kat"]=="prs") & (laþian_df["prefix"]=="0")]))
		write_tex("laþian_bsp_prt_ga", write_example(laþian_df[(laþian_df["g_kat"]=="prt") & (laþian_df["prefix"]=="ge")]))
		
		
		##"normal" telisch
		#settan
		settan_df = df[df["lemma"]=="settan"] 
		write_tex("settan_by_gram", write_table_by_grammar(settan_df))
		write_tex("settan_by_doc", write_table_by_doc(settan_df))
		settan_df = settan_df[~(settan_df["g_kat"]=="perf")]
		write_tex("settan_by_sem", write_table_by_col(settan_df, "sem"))
		settan_probj_df = pd.merge(settan_df["pr_obj"].apply(lambda x: pd.Series(x.split(","))).stack().reset_index(), settan_df.reset_index(), left_on="level_0", right_on="index")
		write_tex("settan_by_probj", write_table_by_col(settan_probj_df, 0))
		write_tex("settan_prt_by_doc", write_table_by_doc(settan_df[(settan_df["g_kat"]=="prt")]))
		write_tex("settan_bsp_inf", write_example(settan_df[(settan_df["g_kat"]=="inf")]))
		write_tex("settan_bsp_inf_0", write_example(settan_df[(settan_df["g_kat"]=="inf") & (settan_df["prefix"]=="0")]))
		write_tex("settan_ein_bsp_inf_0", write_example(settan_df[(settan_df["g_kat"]=="inf") & (settan_df["prefix"]=="0")].iloc[:1]))
		write_tex("settan_bsp_inf_ga", write_example(settan_df[(settan_df["g_kat"]=="inf") & (settan_df["prefix"]=="ge")]))
		write_tex("settan_zwei_bsp_inf_ga", write_example(settan_df[(settan_df["g_kat"]=="inf") & (settan_df["prefix"]=="ge") & (settan_df["line"].isin([1675, 40]))]))
		write_tex("settan_bsp_imp_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["mood"]=="imp")]))
		write_tex("settan_bsp_imp_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["mood"]=="imp")]))
		write_tex("settan_bsp_prt_0", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["prefix"]=="0")]))
		write_tex("settan_bsp_prt_rel_ga", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["clause"]=="relSatz") & (settan_df["prefix"]=="ge")]))
		write_tex("settan_bsp_prt_rel_0", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["clause"]=="relSatz") & (settan_df["prefix"]=="0")]))
		
		write_tex("settan_bsp_put_rest", write_example(settan_df[~(settan_df["g_kat"]=="inf") & ~(settan_df["mood"]=="imp") & (settan_df["sem"]=="put")]))
		write_tex("settan_bsp_verfassen_prt_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["g_kat"]=="prt") & (settan_df["sem"]=="verfassen")]))
		write_tex("settan_zwei_bsp_verfassen_prt_ga", write_example(settan_df[(settan_df["line"].isin([441, 148])) & (settan_df["g_kat"]=="prt") & (settan_df["sem"]=="verfassen")]))
		write_tex("settan_bsp_niederschreiben_swa", write_example(settan_df[(settan_df["conjunction"]=="swā") & (settan_df["sem"]=="niederschreiben")]))
		write_tex("settan_bsp_niederschreiben_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="niederschreiben") & ~(settan_df["conjunction"]=="swā")]))
		write_tex("settan_bsp_niederschreiben_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["sem"]=="niederschreiben") & ~(settan_df["conjunction"]=="swā")]))
		write_tex("settan_zwei_bsp_niederschreiben_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="niederschreiben") & (settan_df["line"].isin([543, 11]))]))
		write_tex("settan_ein_bsp_niederschreiben_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["sem"]=="niederschreiben") & (settan_df["line"].isin([76]))]))
		write_tex("settan_ander_bsp_niederschreiben_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="niederschreiben") & (settan_df["line"].isin([543]))]))
		write_tex("settan_bsp_lock", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="einsperren")]))
		write_tex("settan_bsp_einsetzen_iter_ga", write_example(settan_df[(settan_df["sem"]=="einsetzen") & (settan_df["prefix"]=="ge") & (settan_df["phenomenon"]=="iter")], condense=True))
		write_tex("settan_bsp_einsetzen_0", write_example(settan_df[(settan_df["sem"]=="einsetzen") & (settan_df["prefix"]=="0")], condense=True))
		write_tex("settan_bsp_einsetzen_Or_0", write_example(settan_df[(settan_df["sem"]=="einsetzen") & (settan_df["prefix"]=="0") & (settan_df["doc"]=="Orosius")], condense=True))
		write_tex("settan_ein_bsp_einsetzen_Or_0", write_example(settan_df[(settan_df["sem"]=="einsetzen") & (settan_df["prefix"]=="0") & (settan_df["doc"]=="Orosius") & (settan_df["line"]<120)], condense=True))
		write_tex("settan_bsp_einsetzen_Lt_0", write_example(settan_df[(settan_df["sem"]=="einsetzen") & (settan_df["doc"]=="Letters") & (settan_df["prefix"]=="0")]))
		write_tex("settan_bsp_besiedeln_burg_ga", write_example(settan_df[(settan_df["sem"]=="besiedeln") & (settan_df["prefix"]=="ge") & (settan_df["adjunct"]=="burg")]))
		write_tex("settan_drei_bsp_besiedeln_ga", write_example(settan_df[(settan_df["sem"]=="besiedeln") & (settan_df["prefix"]=="ge") & (settan_df["line"].isin([507, 725, 982]))]))
		write_tex("settan_bsp_festsetzen_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["sem"]=="festsetzen")]))
		write_tex("settan_bsp_festsetzen_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="festsetzen")]))
		write_tex("settan_ein_bsp_festsetzen_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="festsetzen") & (settan_df["line"].isin([828]))]))
		write_tex("settan_ein_bsp_festsetzen_0", write_example(settan_df[(settan_df["prefix"]=="0") & (settan_df["sem"]=="festsetzen") & (settan_df["line"].isin([295]))]))
		write_tex("settan_drei_bsp_festsetzen_ga", write_example(settan_df[(settan_df["prefix"]=="ge") & (settan_df["sem"]=="festsetzen") & (settan_df["line"].isin([84, 235, 828]))]))
		
		write_tex("settan_bsp_prt_Chr", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Chronicle")], condense=True))
		write_tex("settan_bsp_prt_Chr_ga", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Chronicle") & (settan_df["prefix"]=="ge")]))
		write_tex("settan_bsp_prt_Chr_0", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Chronicle") & (settan_df["prefix"]=="0")], condense=True))
		write_tex("settan_bsp_prt_Pref", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Prefaces")]))
		write_tex("settan_bsp_prt_CH", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Catholic Homilies")]))
		write_tex("settan_bsp_Letters_prt_0", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Letters") & (settan_df["prefix"]=="0")]))
		write_tex("settan_bsp_Or_prt_0", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Orosius") & (settan_df["prefix"]=="0")]))
		write_tex("settan_bsp_Or_prt_ga", write_example(settan_df[(settan_df["g_kat"]=="prt") & (settan_df["doc"]=="Orosius") & (settan_df["prefix"]=="ge")]))
		
		#weorpan
		weorpan_df = df[df["lemma"]=="weorpan"]
		write_tex("weorpan_by_gram", write_table_by_grammar(weorpan_df))
		write_tex("weorpan_bsp_ga", write_example(weorpan_df[(weorpan_df["prefix"]=="ge") & ~(weorpan_df["g_kat"]=="perf")]))
		write_tex("weorpan_bsp_0", write_example(weorpan_df[(weorpan_df["prefix"]=="0") & ~(weorpan_df["g_kat"]=="perf")]))
		
		
		#lōgian
		logian_df = df[df["lemma"]=="lōgian"]
		write_tex("logian_by_gram", write_table_by_grammar(logian_df))
		write_tex("logian_bsp_ga", write_example(logian_df[(logian_df["prefix"]=="ge") & ~(logian_df["g_kat"]=="perf")]))
		write_tex("logian_bsp_0", write_example(logian_df[logian_df["prefix"]=="0"]))
		
		#dihtan
		dihtan_df = df[df["lemma"]=="dihtan"]
		write_tex("dihtan_by_gram", write_table_by_grammar(dihtan_df))
		write_tex("dihtan_bsp_inf_0", write_example(dihtan_df[(dihtan_df["g_kat"]=="inf") & (dihtan_df["prefix"]=="0")]))
		write_tex("dihtan_bsp_prs_0", write_example(dihtan_df[(dihtan_df["g_kat"]=="prs") & (dihtan_df["prefix"]=="0")]))
		write_tex("dihtan_bsp_prt_0", write_example(dihtan_df[(dihtan_df["g_kat"]=="prt") & (dihtan_df["prefix"]=="0")]))
		write_tex("dihtan_bsp_prt_akk_ga", write_example(dihtan_df[(dihtan_df["g_kat"]=="prt") & (dihtan_df["obj_case"]=="akk") & (dihtan_df["prefix"]=="ge")]))
		write_tex("dihtan_bsp_prt_0_ga", write_example(dihtan_df[(dihtan_df["g_kat"]=="prt") & (dihtan_df["object"]=="0") & (dihtan_df["prefix"]=="ge")]))
		
		#wrītan
		writan_df = df[df["lemma"]=="wrītan"]
		write_tex("writan_by_gram", write_table_by_grammar(writan_df))
		write_tex("writan_bsp_ga", write_example(writan_df[~(writan_df["g_kat"]=="perf") & (writan_df["prefix"]=="ge")]))
		write_tex("writan_bsp_rel_0", write_example(writan_df[(writan_df["clause"]=="relSatz") & (writan_df["prefix"]=="0")]))
		write_tex("writan_bsp_sg_0", write_example(writan_df[(writan_df["number"]=="sg") & (writan_df["sem"]=="inhalt") & (writan_df["prefix"]=="0")]))
		write_tex("writan_bsp_schneiden", write_example(writan_df[(writan_df["sem"]=="schneiden")]))
		write_tex("writan_bsp_perf", write_example(writan_df[(writan_df["g_kat"]=="perf") & (writan_df["prefix"]=="ge")]))
		
		#dǣlan
		dælan_df = df[df["lemma"]=="d\\textaemacron{}lan"]
		write_tex("dælan_by_gram", write_table_by_grammar(dælan_df))
		write_tex("dælan_bsp_bel", write_example(dælan_df[(dælan_df["belebt"]=="bel")]))
		write_tex("dælan_bsp_prt_ga", write_example(dælan_df[(dælan_df["g_kat"]=="prt") & (dælan_df["belebt"]=="unbel") & (dælan_df["prefix"]=="ge")]))
		write_tex("dælan_bsp_teilen_0", write_example(dælan_df[(dælan_df["sem"]=="teilen") & (dælan_df["prefix"]=="0")]))
		write_tex("dælan_bsp_zerteilen_0", write_example(dælan_df[(dælan_df["sem"]=="zerteilen") & (dælan_df["prefix"]=="0")]))
		write_tex("dælan_bsp_verteilen_0", write_example(dælan_df[(dælan_df["sem"]=="verteilen") & (dælan_df["prefix"]=="0")]))
		
		#wrecan
		wrecan_df = df[df["lemma"]=="wrecan"]
		write_tex("wrecan_by_gram", write_table_by_grammar(wrecan_df))
		write_tex("wrecan_by_doc", write_table_by_doc(wrecan_df))
		write_tex("wrecan_bsp_inf_ga", write_example(wrecan_df[(wrecan_df["g_kat"]=="inf") & (wrecan_df["prefix"]=="ge")]))
		write_tex("wrecan_ein_bsp_inf_ga", write_example(wrecan_df[(wrecan_df["g_kat"]=="inf") & (wrecan_df["prefix"]=="ge") & (wrecan_df["doc"]=="Orosius")].iloc[:1]))
		write_tex("wrecan_bsp_inf_0", write_example(wrecan_df[(wrecan_df["g_kat"]=="inf") & (wrecan_df["prefix"]=="0")]))
		write_tex("wrecan_bsp_prt_ga", write_example(wrecan_df[(wrecan_df["g_kat"]=="prt") & (wrecan_df["prefix"]=="ge")]))
		write_tex("wrecan_bsp_prt_0", write_example(wrecan_df[(wrecan_df["g_kat"]=="prt") & (wrecan_df["prefix"]=="0")]))
		write_tex("wrecan_bsp_ger", write_example(wrecan_df[(wrecan_df["g_kat"]=="ger")]))
		write_tex("wrecan_bsp_bel_ga", write_example(wrecan_df[(wrecan_df["belebt"]=="bel") & (wrecan_df["prefix"]=="ge")]))
		
		#dreċċan
		dreccan_df = df[df["lemma"]=="dreċċan"]
		write_tex("dreccan_by_gram", write_table_by_grammar(dreccan_df))
		write_tex("dreccan_by_doc", write_table_by_doc(dreccan_df))
		write_tex("dreccan_bsp_ga", write_example(dreccan_df[(dreccan_df["prefix"]=="ge") & ~(dreccan_df["g_kat"]=="perf")]))
		write_tex("dreccan_bsp_0", write_example(dreccan_df[(dreccan_df["prefix"]=="0") & ~(dreccan_df["g_kat"]=="perf")]))
		
		#feallan
		feallan_df = df[df["lemma"]=="feallan"]
		write_tex("feallan_by_gram", write_table_by_grammar(feallan_df))
		write_tex("feallan_ein_bsp_prt_0", write_example(feallan_df[(feallan_df["g_kat"]=="prt") & (feallan_df["prefix"]=="0")].iloc[0:1,:]))
		write_tex("feallan_bsp_prt_ga", write_example(feallan_df[(feallan_df["g_kat"]=="prt") & (feallan_df["prefix"]=="ge")]))
		
		#ċierran
		cierran_df = df[df["lemma"]=="ċierran"]
		write_tex("cierran_by_gram", write_table_by_grammar(cierran_df))
		write_tex("cierran_by_doc", write_table_by_doc(cierran_df))
		write_tex("cierran_by_sem", write_table_by_col(cierran_df, "sem"))
		write_tex("cierran_bsp_inf", write_example(cierran_df[(cierran_df["g_kat"]=="inf")]))
		write_tex("cierran_bsp_prs", write_example(cierran_df[(cierran_df["g_kat"]=="prs") & ~(cierran_df["mood"]=="prc")]))
		write_tex("cierran_bsp_prs_heim", write_example(cierran_df[(cierran_df["sem"]=="heimkehren")]))
		write_tex("cierran_bsp_prt_ga", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="ge")]))
		write_tex("cierran_bsp_prt_butan", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["doc"]=="Chronicle") & (cierran_df["line"].isin([1010, 1103]))]))
		write_tex("cierran_bsp_prt_ga_Chron", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="ge") & (cierran_df["doc"]=="Chronicle")]))
		write_tex("cierran_bsp_prt_ga_unterwerfen", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="ge") & (cierran_df["sem"].str.contains("unterwerfen"))]))
		write_tex("cierran_bsp_prt_ga_unterwerfen_Chron", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="ge") & (cierran_df["sem"].str.contains("unterwerfen")) & (cierran_df["doc"]=="Chronicle")]))
		write_tex("cierran_bsp_prt_ga_übertragen", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="ge") & (cierran_df["sem"]=="übertragen")]))
		write_tex("cierran_bsp_prt_0", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="0")]))
		write_tex("cierran_ein_bsp_prt_0", write_example(cierran_df[(cierran_df["g_kat"]=="prt") & (cierran_df["prefix"]=="0")].iloc[:1]))
		write_tex("cierran_ein_bsp_ga_bekehren", write_example(cierran_df[(cierran_df["prefix"]=="ge") & (cierran_df["sem"]=="bekehren")].iloc[:1]))
		
		#wendan
		wendan_df = df[df["lemma"]=="wendan"]
		write_tex("wendan_by_gram", write_table_by_grammar(wendan_df))
		write_tex("wendan_prt_by_adj", write_table_by_col(wendan_df[(wendan_df["g_kat"]=="prt")], "adjunct"))
		write_tex("wendan_prt_by_doc", write_table_by_doc(wendan_df[(wendan_df["g_kat"]=="prt")]))
		write_tex("wendan_bsp_inf", write_example(wendan_df[wendan_df["g_kat"]=="inf"]))
		write_tex("wendan_bsp_prt_abstrakt_0", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & ~(wendan_df["sem"]=="motion") & (wendan_df["prefix"]=="0")]))
		write_tex("wendan_ein_bsp_prt_abstrakt_0", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & ~(wendan_df["sem"]=="motion") & (wendan_df["prefix"]=="0")].iloc[:1]))
		write_tex("wendan_bsp_prt_ga", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & (wendan_df["prefix"]=="ge")]))
		write_tex("wendan_ein_bsp_prt_ga", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & (wendan_df["prefix"]=="ge") & (wendan_df["line"]==1009)]))
		write_tex("wendan_bsp_prt_ham_0", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & (wendan_df["object"]=="0") & (wendan_df["adverb"]=="hāmweard") & (wendan_df["prefix"]=="0")]))
		write_tex("wendan_ein_bsp_prt_ham_0", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & (wendan_df["object"]=="0") & (wendan_df["adverb"]=="hāmweard") & (wendan_df["prefix"]=="0") & (wendan_df["line"]==1456)]))
		write_tex("wendan_ander_bsp_prt_ham_0", write_example(wendan_df[(wendan_df["g_kat"]=="prt") & (wendan_df["object"]=="0") & (wendan_df["adverb"]=="hāmweard") & (wendan_df["prefix"]=="0") & (wendan_df["line"]==1072)]))
		
		#hweorfan
		hweorfan_df = df[df["lemma"]=="hweorfan"]
		write_tex("hweorfan_by_gram", write_table_by_grammar(hweorfan_df))
		write_tex("hweorfan_by_doc", write_table_by_doc(hweorfan_df))
		write_tex("hweorfan_bsp_ga", write_example(hweorfan_df[(hweorfan_df["prefix"]=="ge") & ~(hweorfan_df["g_kat"]=="perf")]))
		write_tex("hweorfan_bsp_0", write_example(hweorfan_df[(hweorfan_df["prefix"]=="0") & (hweorfan_df["object"]=="0")]))
		
		#nēahlǣcan
		neahlæcan_df = df[df["lemma"]=="nēahl\\textaemacron{}can"]
		write_tex("neahlæcan_by_gram", write_table_by_grammar(neahlæcan_df))
		write_tex("neahlæcan_bsp_prt_ga", write_example(neahlæcan_df[(neahlæcan_df["g_kat"]=="prt") & (neahlæcan_df["prefix"]=="ge")]))
		write_tex("neahlæcan_bsp_prt_0", write_example(neahlæcan_df[(neahlæcan_df["g_kat"]=="prt") & (neahlæcan_df["prefix"]=="0")]))
		
		#niman (?gehört das hierhin?)
		niman_df = df[df["lemma"]=="niman"]
		write_tex("niman_by_gram", write_table_by_grammar(niman_df))
		write_tex("niman_by_doc", write_table_by_doc(niman_df))
		write_tex("niman_prt_by_doc", write_table_by_doc(niman_df[niman_df["g_kat"]=="prt"]))
		write_tex("niman_by_obj", write_table_by_col(niman_df[~(niman_df["g_kat"]=="perf")], "adjunct"))
		write_tex("niman_bsp_prt_Sigeweard_0", write_example(niman_df[(niman_df["page"]=="To Sigeweard") & (niman_df["g_kat"]=="prt") & (niman_df["prefix"]=="0")]))
		write_tex("niman_bsp_hine", write_example(niman_df[(niman_df["adjunct"]=="hine")].sort_values("line")))
		write_tex("niman_zwei_bsp_hine", write_example(niman_df[(niman_df["adjunct"]=="hine")].sort_values("line").iloc[:2]))
		write_tex("niman_bsp_eall", write_example(niman_df[(niman_df["adjunct"]=="eall")]))
		write_tex("niman_bsp_ic_genam", write_example(niman_df[(niman_df["gram"]=="1.sg.ind.prt.")]))
		write_tex("niman_bsp_friþ_ga", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="ge")]))
		write_tex("niman_ein_bsp_friþ_ga", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="ge")].iloc[:1]))
		write_tex("niman_paar_bsp_friþ_ga", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="ge") & ~(niman_df["doc"]=="Orosius")]))
		write_tex("niman_ander_bsp_friþ_ga", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="ge") & (niman_df["line"].isin([174]))]))
		write_tex("niman_bsp_friþ_0", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="0")]))
		write_tex("niman_ein_bsp_friþ_0", write_example(niman_df[(niman_df["adjunct"]=="friþ") & (niman_df["prefix"]=="0")].iloc[:1]))
		
		#þiċġan
		þicgan_df = df[df["lemma"]=="þiċġan"]
		write_tex("þicgan_by_gram", write_table_by_grammar(þicgan_df))
		write_tex("þicgan_bsp_inf_ga", write_example(þicgan_df[(þicgan_df["g_kat"]=="inf") & (þicgan_df["prefix"]=="ge")].sort_values("line")))
		write_tex("þicgan_ein_bsp_inf_ga", write_example(þicgan_df[(þicgan_df["g_kat"]=="inf") & (þicgan_df["prefix"]=="ge") & (þicgan_df["line"].isin([588]))]))
		write_tex("þicgan_ander_bsp_inf_ga", write_example(þicgan_df[(þicgan_df["g_kat"]=="inf") & (þicgan_df["prefix"]=="ge") & (þicgan_df["line"].isin([600]))]))
		write_tex("þicgan_bsp_inf_0", write_example(þicgan_df[(þicgan_df["g_kat"]=="inf") & (þicgan_df["prefix"]=="0")]))
		write_tex("þicgan_zwei_bsp_inf_0", write_example(þicgan_df[(þicgan_df["g_kat"]=="inf") & (þicgan_df["prefix"]=="0") & (þicgan_df["line"].isin([230, 962]))]))
		write_tex("þicgan_ein_bsp_prt_0_Or", write_example(þicgan_df[(þicgan_df["g_kat"]=="prt") & (þicgan_df["prefix"]=="0") & (þicgan_df["line"].isin([595]))]))
		
		#lǣċan
		læcan_df = df[df["lemma"]=="l\\textaemacron{}ċan"]
		write_tex("læcan_by_gram", write_table_by_grammar(læcan_df))
		write_tex("læcan_bsp_prt_ga", write_example(læcan_df[(læcan_df["g_kat"]=="prt") & (læcan_df["prefix"]=="ge")]))
		write_tex("læcan_bsp_prt_0", write_example(læcan_df[(læcan_df["g_kat"]=="prt") & (læcan_df["prefix"]=="0")]))
		write_tex("læcan_bsp_prs_ga", write_example(læcan_df[(læcan_df["g_kat"]=="prs") & (læcan_df["prefix"]=="ge")]))
		
		#ċēapian
		ceapian_df = df[df["lemma"]=="ċēapian"]
		write_tex("ceapian_by_gram", write_table_by_grammar(ceapian_df))
		write_tex("ceapian_bsp_prt_ga", write_example(ceapian_df[(ceapian_df["g_kat"]=="prt") & (ceapian_df["prefix"]=="ge")]))
		write_tex("ceapian_zwei_bsp_Or", write_example(ceapian_df[(ceapian_df["g_kat"]=="prt") & (ceapian_df["prefix"]=="0") | (ceapian_df["g_kat"]=="inf")], condense=True))
		
		#bringan
		##perfekt → s.o.
		bringan_df = df[df["lemma"]=="bringan"].copy()
		write_tex("bringan_by_gram", write_table_by_grammar(bringan_df))
		write_tex("bringan_by_doc", write_table_by_doc(bringan_df))
		
		bringan_df.loc[:,"author"] = bringan_df.loc[:,"doc"].apply(lambda x: re.sub("Letters|Catholic Homilies|Prefaces", "Ælfric", x))
		write_tex("chi2_bringan_text_sem", chi2(bringan_df[~(bringan_df["doc"]=="Marvels")], "sem", "author"))
		
		write_tex("bringan_bsp_prt_ga", write_example(bringan_df[(bringan_df["g_kat"]=="prt") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_prt_0", write_example(bringan_df[(bringan_df["g_kat"]=="prt") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_prs_ga", write_example(bringan_df[(bringan_df["g_kat"]=="prs") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_prs_0", write_example(bringan_df[(bringan_df["g_kat"]=="prs") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_ind_prs", write_example(bringan_df[(bringan_df["g_kat"]=="prs") & (bringan_df["mood"]=="ind")]))
		write_tex("bringan_bsp_inf_ga", write_example(bringan_df[(bringan_df["g_kat"]=="inf") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_inf_0", write_example(bringan_df[(bringan_df["g_kat"]=="inf") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_dass", write_example(bringan_df[(bringan_df["object"]=="dassSatz")]))
		write_tex("bringan_bsp_prt_to_ga", write_example(bringan_df[(bringan_df["pr_obj"].str.match("tō")) & (bringan_df["g_kat"]=="prt") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_prt_rel_ga", write_example(bringan_df[(bringan_df["clause"].str.match("relSatz")) & (bringan_df["g_kat"]=="prt")]))
		
		
		bringan_df = bringan_df[~(bringan_df["g_kat"]=="perf")]
		write_tex("bringan_by_sem", write_table_by_col(bringan_df, "sem", sort="total"))
		write_tex("bringan_bsp_geleiten", write_example(bringan_df[(bringan_df["sem"]=="geleiten")].sort_values(["prefix"])))
		write_tex("bringan_bsp_geleiten_0", write_example(bringan_df[(bringan_df["sem"]=="geleiten") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_geleiten_ga", write_example(bringan_df[(bringan_df["sem"]=="geleiten") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_ein_bsp_geleiten_ga", write_example(bringan_df[(bringan_df["sem"]=="geleiten") & (bringan_df["prefix"]=="ge")].iloc[:1]))
		write_tex("bringan_ein_bsp_geleiten_imp", write_example(bringan_df[(bringan_df["sem"]=="geleiten") & (bringan_df["prefix"]=="ge") & (bringan_df["line"].isin([1053]))]))
		write_tex("bringan_zwei_bsp_geleiten_ga", write_example(bringan_df[(bringan_df["sem"]=="geleiten") & (bringan_df["prefix"]=="ge") & (bringan_df["line"].isin([960, 967]))]))
		write_tex("bringan_bsp_gebären", write_example(bringan_df[(bringan_df["sem"]=="gebären")]))
		write_tex("bringan_bsp_mitbringen_ga", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_mitbringen_0", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_mitbringen_0_Ælf", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["prefix"]=="0") & (bringan_df["author"]=="Ælfric")]))
		write_tex("bringan_bsp_mitbringen_prn", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["object"]=="prn")]))
		write_tex("bringan_bsp_mitbringen_sub", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["object"]=="sub")]))
		write_tex("bringan_bsp_mitbringen_bel", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["belebt"].isin(["anim", "bel?"]))]))
		write_tex("bringan_bsp_mitbringen_unbel", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["belebt"]=="unbel")]))
		write_tex("bringan_bsp_mitbringen_unbel_0", write_example(bringan_df[(bringan_df["sem"]=="mitbringen") & (bringan_df["belebt"]=="unbel") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_übertragen_0", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["prefix"]=="0")].sort_values(["adjunct"])))
		write_tex("bringan_ein_bsp_übertragen_0", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["prefix"]=="0") & (bringan_df["line"].isin([437]))]))
		write_tex("bringan_zwei_bsp_übertragen_0", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["prefix"]=="0") & (bringan_df["line"].isin([437, 556]))]))
		write_tex("bringan_bsp_übertragen_inf", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["g_kat"]=="inf")]))
		write_tex("bringan_ein_bsp_übertragen_inf", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["g_kat"]=="inf") & ~(bringan_df["doc"]=="Orosius")]))
		write_tex("bringan_zwei_bsp_übertragen_inf", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["g_kat"]=="inf") & ~(bringan_df["match"]=="brengan")]))
		write_tex("bringan_bsp_übertragen_bel_ga", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["belebt"].str.match("bel")) & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_übertragen_unbel_ga", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["belebt"]=="unbel") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_übertragen_Chron", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["doc"]=="Chronicle")]))
		write_tex("bringan_paar_bsp_übertragen_ga", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["line"].isin([401, 184, 87])) & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_zwei_bsp_übertragen_ga", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["line"].isin([134, 342])) & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_ein_bsp_übertragen_ga", write_example(bringan_df[(bringan_df["sem"]=="übertragen") & (bringan_df["line"].isin([134])) & (bringan_df["prefix"]=="ge")]))
		
		write_tex("bringan_by_bel", write_table_by_col(bringan_df, "belebt"))
		write_tex("bringan_bsp_bel", write_example(bringan_df[(bringan_df["belebt"]=="bel")]))
		write_tex("bringan_bsp_bel_ga", write_example(bringan_df[(bringan_df["belebt"]=="bel") & (bringan_df["prefix"]=="ge")]))
		write_tex("bringan_bsp_bel_0", write_example(bringan_df[(bringan_df["belebt"]=="bel") & (bringan_df["prefix"]=="0")]))
		write_tex("bringan_bsp_bel2", write_example(bringan_df[(bringan_df["belebt"].isin(["bel?", "anim"]))]))
		write_tex("bringan_bsp_unbel_abs", write_example(bringan_df[(bringan_df["belebt"]=="unbel") & (bringan_df["adjunct"].isin(["trīumpha", "sibb"]))]))
		write_tex("bringan_bsp_unbel_prn", write_example(bringan_df[(bringan_df["belebt"]=="unbel") & (bringan_df["object"]=="prn") & ~(bringan_df["clause"].str.contains("relSatz"))]))
		write_tex("bringan_bsp_prt_unbel_ga", write_example(bringan_df[(bringan_df["belebt"]=="unbel") & (bringan_df["g_kat"]=="prt") & (bringan_df["prefix"]=="ge")]))
		
		write_tex("bringan_bsp_Or_985", write_example(bringan_df[(bringan_df["doc"]=="Orosius") & (bringan_df["line"]==985)]))
		
		#sellan
		sellan_df = df[df["lemma"]=="sellan"]
		write_tex("sellan_by_gram", write_table_by_grammar(sellan_df))
		sellan_df = sellan_df[~(sellan_df["g_kat"]=="perf")]
		write_tex("sellan_by_obj_bel", write_table_by_col(sellan_df[(sellan_df["belebt"]=="bel")], "adjunct"))
		write_tex("sellan_bsp_inf", write_example(sellan_df[(sellan_df["g_kat"]=="inf")]))
		write_tex("sellan_bsp_prt_ga", write_example(sellan_df[(sellan_df["g_kat"]=="prt") & (sellan_df["prefix"]=="ge")]))
		write_tex("sellan_bsp_bel_ga", write_example(sellan_df[(sellan_df["belebt"]=="bel") & (sellan_df["prefix"]=="ge")]))
		write_tex("sellan_bsp_bel_prn", write_example(sellan_df[(sellan_df["belebt"]=="bel") & (sellan_df["adjunct"]=="hīe")]))
		write_tex("sellan_bsp_bel_0", write_example(sellan_df[(sellan_df["belebt"]=="bel") & (sellan_df["prefix"]=="0")]))
		write_tex("sellan_bsp_prn_unbel_ga", write_example(sellan_df[(sellan_df["object"]=="prn") & (sellan_df["belebt"]=="unbel") & (sellan_df["prefix"]=="ge")]))
		write_tex("sellan_bsp_prn_unbel_0", write_example(sellan_df[(sellan_df["object"]=="prn") & (sellan_df["belebt"]=="unbel") & (sellan_df["prefix"]=="0")]))
		write_tex("sellan_bsp_prn_unbel_Or", write_example(sellan_df[(sellan_df["object"]=="prn") & (sellan_df["belebt"]=="unbel") & (sellan_df["doc"]=="Orosius")]))
		
		write_tex("sellan_bsp_sterben", write_example(sellan_df[(sellan_df["adjunct"]=="feorh")]))
		write_tex("sellan_ein_bsp_sterben", write_example(sellan_df[(sellan_df["adjunct"]=="feorh")].iloc[:1]))
		write_tex("sellan_bsp_feoh", write_example(sellan_df[(sellan_df["adjunct"].str.contains("feoh"))]))
		write_tex("sellan_zwei_bsp_feoh", write_example(sellan_df[(sellan_df["adjunct"].str.contains("feoh")) & (sellan_df["doc"]=="Chronicle")]))
		write_tex("sellan_bsp_land", write_example(sellan_df[(sellan_df["adjunct"].isin(["land", "dǣl", "mynster", "sum"]))].sort_values("line")))
		
		#etan
		etan_df = df[df["lemma"]=="etan"]
		write_tex("etan_by_gram", write_table_by_grammar(etan_df))
		write_tex("etan_bsp_prt_ga", write_example(etan_df[(etan_df["g_kat"]=="prt") & (etan_df["prefix"]=="ge")]))
		write_tex("etan_bsp_prt_0", write_example(etan_df[(etan_df["g_kat"]=="prt") & (etan_df["prefix"]=="0")]))
		
	write_lemma()
	
	##Satzarten
	def write_clause():
		write_tex("clause_temp_siþþan", write_table_by_lemma(df[df["conjunction"]=="siþþan"]))
		
		
		#Relativsätze
		rel_df = df[(df["clause"].str.contains("relSatz")) & ~(df["g_kat"]=="perf") & ~(df["person"]=="-") & ~(df["status"].isin(["fest"]))]
		
		write_tex("relSatz", lemma_pivot(rel_df, incl_zero=True, incl_pref=True, sort="percentage"))
		
		write_tex("relSatz_cnj_prs_by_lemma", write_table_by_col(rel_df[rel_df["gram"].str.contains("cnj.prs.")], "lemma", sort="total"))
		write_tex("relSatz_cnj_prt_by_lemma", write_table_by_col(rel_df[rel_df["gram"].str.contains("cnj.prt.")], "lemma", sort="total"))
		
		write_tex("relSatz_cnj_prs_ga", write_example(rel_df[(rel_df["gram"].str.contains("cnj.prs.")) & (rel_df["prefix"]=="ge")]))
		write_tex("relSatz_cnj_prs_0", write_example(rel_df[(rel_df["gram"].str.contains("cnj.prs.")) & (rel_df["prefix"]=="0")]))
		
		write_tex("relSatz_cnj_prt_ga", write_example(rel_df[(rel_df["gram"].str.contains("ind.prt.")) & (rel_df["prefix"]=="ge")]))
		write_tex("relSatz_cnj_prt_0", write_example(rel_df[(rel_df["gram"].str.contains("cnj.prt.")) & (rel_df["prefix"]=="0")]))
		
		rel_df = rel_df[rel_df["lemma"].isin(["healdan", "hīeran", "bēodan", "līcian", "timbran", "cweþan", "l\\textaemacron{}dan", "bringan", "singan", "scēawian", "būgan", "settan", "wyrċan", "wissian", "fullian"])]
		
		write_tex("relSatz_ind_prs_by_lemma", write_table_by_col(rel_df[rel_df["gram"].str.contains("ind.prs.")], "lemma", sort="total"))
		write_tex("relSatz_ind_prt_by_lemma", write_table_by_col(rel_df[rel_df["gram"].str.contains("ind.prt.")], "lemma", sort="total"))
	
		write_tex("relSatz_ind_prs_ga", write_example(rel_df[(rel_df["gram"].str.contains("ind.prs.")) & (rel_df["lemma"].isin(["dōn", "cweþan", "fullian", "scēawian"])) & (rel_df["prefix"]=="ge")]))
		write_tex("relSatz_ind_prs_0", write_example(rel_df[(rel_df["gram"].str.contains("ind.prs.")) & (rel_df["lemma"].isin(["dōn", "cweþan", "fullian", "scēawian"])) & (rel_df["prefix"]=="0")]))
		
		write_tex("relSatz_ind_prt_ga", write_example(rel_df[(rel_df["gram"].str.contains("ind.prt.")) & (rel_df["lemma"].isin(["cweþan", "settan", "hīeran", "wyrċan", "bringan", "healdan", "timbran", "būgan"])) & (rel_df["prefix"]=="ge")]))
		write_tex("relSatz_ind_prt_0", write_example(rel_df[(rel_df["gram"].str.contains("ind.prt.")) & (rel_df["lemma"].isin(["cweþan", "settan", "hīeran", "wyrċan", "bringan", "healdan", "timbran", "būgan"])) & (rel_df["prefix"]=="0")]))
	write_clause()
	
	
	#Konjunktiv
	write_tex("Konjunktiv_count", write_table(df[df["gram"].str.contains(cnj_str)]))
	write_tex("cnj_prs_dass_by_doc", write_table_by_doc(df[(df["mood"]=="cnj") & (df["clause"]=="dassSatz") & (df["g_kat"]=="prs")]))
	write_tex("ind_prs_dass_by_doc", write_table_by_doc(df[(df["mood"]=="ind") & (df["clause"]=="dassSatz") & (df["g_kat"]=="prs")]))
	
	write_tex("cnj_prs_lemma_count", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prs") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, incl_zero=True))
	write_tex("cnj_prs_lemma_count_ga", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prs") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, no_zero=True))
	write_tex("cnj_prs_lemma_count_0", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prs") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], no_pref=True, incl_zero=True))
	
	write_tex("cnj_prt_lemma_count", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prt") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, incl_zero=True))
	write_tex("cnj_prt_lemma_count_ga", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prt") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, no_zero=True))
	write_tex("cnj_prt_lemma_count_0", lemma_pivot(df[(df["mood"]=="cnj") & (df["tempus"]=="prt") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], no_pref=True, incl_zero=True))
	
	#Imperativ
	write_tex("Imperativ_by_doc", write_table_by_doc(df[df["g_kat"]=="imp"]))
	write_tex("Imperativ_by_lemma", lemma_pivot(df[(df["g_kat"]=="imp") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))]))
	
	write_tex("imp_lemma_count", lemma_pivot(df[(df["g_kat"]=="imp") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, incl_zero=True))
	write_tex("imp_lemma_count_ga", lemma_pivot(df[(df["g_kat"]=="imp") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], incl_pref=True, no_zero=True))
	write_tex("imp_lemma_count_0", lemma_pivot(df[(df["g_kat"]=="imp") & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(exclude))], no_pref=True, incl_zero=True))
	
	
	unperfekt_df = df[~(df["g_kat"]=="perf")]
	#Modaladverbialia
	write_tex("modaladv_by_doc", write_table_by_grammar(unperfekt_df[~(unperfekt_df["adverb_mod"]=="") & ~(unperfekt_df["clause"].str.contains("Frag"))]))
	write_tex("modaladv_frag_by_doc", write_table_by_grammar(unperfekt_df[~(unperfekt_df["adverb_mod"]=="") & (unperfekt_df["clause"].str.contains("Frag"))]))

	
	#Infinitive
	write_tex("bsp_sculan", write_table_by_doc(df[(df["rektion"]=="sculan")]))
	
			
	print("saved tex")
	
def problemstellen():
	write_tex("wyrcan_sem", write_example(df[(df["sem"]=="") & (df["lemma"]=="wyrċan") & ~(df["g_kat"]=="perf")]))
	write_tex("þyilcangeare", write_table_by_lemma(df[df["adverb_tmp"]=="þ\\textymacron{}"]))
	write_tex("siþþan", write_table_by_lemma(df[(df["adverb_tmp"]=="siþþan") & ~(df["g_kat"]=="perf")]))
	write_tex("oft", write_table_by_lemma(df[(df["adverb_tmp"].isin(["oft", "ġelōme"])) & ~(df["g_kat"]=="perf")]))
	write_tex("nū", write_table_by_lemma(df[(df["adverb_tmp"].isin(["nū"])) & ~(df["g_kat"]=="perf")]))
	write_tex("ær", write_table_by_col(df[(df["conjunction"].str.match("^\\\\textaemacron{}r"))], "g_kat", sort="total"))
	write_tex("ær_prt", write_table_by_col(df[(df["conjunction"].str.match("^\\\\textaemacron{}r")) & (df["g_kat"]=="prt")], "lemma", sort="percentage"))
	write_tex("beþamþe", write_example(df[df["comment"]=="beþamþe"]))
	write_tex("problem_settan", write_example(df[(df["comment"]=="Übersetzung?") & (df["lemma"]=="settan")], alt=True))
	write_tex("eUe", write_example(df[(df["comment"]=="Übersetzung?") & (df["trans_anm"]=="\eUe")]))
	write_tex("eac", lemma_pivot(df[(df["adverb"]=="ēac") & ~(df["g_kat"]=="inf")]))
	write_tex("belebtheit", write_example(df[(df["belebt"]=="bel?")]))
	write_tex("willan", write_table_by_col(df[(df["rektion"]=="willan")], "lemma", sort="total", non_zero=["ge", "0"]))
	
	out = ""
	
	problem_df = df[df["comment"].str.contains("\?")]
	for comment, dff in problem_df.groupby("comment"):
		out += "\\subsection*{{{}}}\n\n".format(comment)
		out += write_example(dff, alt=True, verbose=["lemma", "gram"])
		
	clause_problem_df = df[df["clause"].str.contains("\?")]
	for clause, dff in clause_problem_df.groupby("clause"):
		out += "\\subsection*{{{}}}\n\n".format(comment)
		out += write_example(dff, alt=True, verbose=["lemma", "gram"])
	
	write_tex("problemstellen", out)
	
def interessant():
	out = ""
	
	problem_df = df[df["comment"].str.contains("!")]
	
	for comment, dff in problem_df.groupby("comment"):
		out += "\\subsection*{{{}}}\n\n".format(comment)
		out += write_example(dff, alt=True, verbose=["lemma", "gram"])
		
	write_tex("interessant", out)

def computation_heavy():
	global df
	def list_col(current_df, column_name, italics=False):
		if column_name in current_df:
			if italics:
				return "\\\\\n".join(["\\textit{{{}}}".format(lm) for lm in current_df[column_name].unique()])
				
			else:
				return "\\\\\n".join(current_df[column_name].unique())
		else:
			return column_name + " not in dataframe"
	
	exclude = ["aux", "keep", "modalverb"]
	exclude_strict = exclude + ["unpräf"]

	#Zahlen und Tabellen zur Übersicht
	if count_rows and count_words:
		write_tex("count_rows", format_number(count_rows))
		write_tex("count_words", format_number(count_words))
	write_tex("count_all_matches", format_number(count_all_matches))
	write_tex("count_excluded", format_number(count_all_matches-df.shape[0]))
	
	active_corpus = df[(~df["status"].isin(["modalverb", "aux", "nomen", "hidden", "keep"]) & (df["prefix"].isin(["0", "ge"])))]
	write_tex("flexible_lemma_count", lemma_pivot(active_corpus, sort="total"))
	
	write_tex("overview_by_doc", write_table_by_doc(active_corpus[(~active_corpus["status"].isin(exclude))]))
	write_tex("overview_by_gram", write_table_by_grammar(active_corpus[(~active_corpus["status"].isin(exclude))]))
	
	write_tex("overview_pos", write_table_by_grammar(active_corpus[active_corpus["negation"]=="0"]))
	write_tex("overview_neg", write_table_by_grammar(active_corpus[~(active_corpus["negation"]=="0")]))
	
	write_tex("total_count", write_example(df, return_number=True))
	write_tex("complete_ga", write_example(active_corpus[active_corpus["prefix"]=="ge"], return_number=True))
	write_tex("unpräf_count", write_example(active_corpus[active_corpus["prefix"]=="0"], return_number=True))
	write_tex("active_corpus", write_example(active_corpus, return_number=True))
	write_tex("aux_count", write_example(df[df["status"]=="aux"], return_number=True))
	write_tex("modalverb_count", write_example(df[df["status"]=="modalverb"], return_number=True))
	write_tex("nomen_count", write_example(df[df["status"]=="nomen"], return_number=True))
	write_tex("fest", list_col(df[df["status"]=="fest"].sort_values("lemma"), "lemma", True))
	write_tex("q-hapax", list_col(df[df["status"]=="q-hapax"].sort_values("lemma"), "lemma", True))
	write_tex("q-hapax_fest", lemma_pivot(df[df["status"].isin(("q-hapax", "fest", "hapax"))], sort="total"))
	write_tex("prc-only", lemma_pivot(df[(df["status"]=="prc-only") & ~(df["lemma"].isin(df[(df["status"]=="prc-only") & (df["g_kat"]=="perf") & (df["prefix"]=="0")]["lemma"].unique()))], sort="total"))
	write_tex("q-hapax_count", write_example(df[df["status"].isin(("q-hapax", "fest"))], return_number=True))
	write_tex("keep_count", write_example(df[df["status"].isin(("keep", "unpräf"))], return_number=True))
	write_tex("q-hapax_leftovers", lemma_pivot(df[(df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(["fest", "hapax", "q-hapax"]))].sort_values("lemma"), no_zero=True))
	write_tex("q-hapax_Ælfric", lemma_pivot(df[(df["doc"].isin(["Letters", "Prefaces", "Catholic Homilies"])) & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(["fest", "hapax", "q-hapax"]))].sort_values("lemma"), no_zero=True))
	write_tex("q-hapax_Or", lemma_pivot(df[(df["doc"].isin(["Orosius"])) & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(["fest", "hapax", "q-hapax"]))].sort_values("lemma"), no_zero=True))
	write_tex("q-hapax_Chr", lemma_pivot(df[(df["doc"].isin(["Chronicle"])) & (df["prefix"].isin(["ge", "0"])) & (~df["status"].isin(["fest", "hapax", "q-hapax"]))].sort_values("lemma"), no_zero=True))
	
	write_tex("chi2_tempus", chi2(active_corpus[~active_corpus["g_kat"].isin(["perf", "ger", "inf"])], "prefix", "tempus"))
	
	write_tex("bsp_neg_ga", write_example(df[~(df["negation"]=="0") & ~(df["g_kat"]=="perf") & (df["prefix"]=="ge")], True))
	
	df = df[df["prefix"].isin(["ge", "0"])]
	
	write_tex("lemma_gram_prt_only", lemma_pivot(df, incl_pref={"g_kat" : ["prt"]}, incl_zero={"g_kat" : ["prs"]}, no_pref={"g_kat" : ["prs"]}, no_zero={"g_kat" : ["prt"]}))
	write_tex("lemma_temp_prt_only", lemma_pivot(df, incl_pref={"tempus" : ["prt"]}, incl_zero={"tempus" : ["prs"]}, no_pref={"tempus" : ["prs"]}, no_zero={"tempus" : ["prt"]}))
	write_tex("lemma_gram_prs_only", lemma_pivot(df, incl_pref={"g_kat" : ["prs"]}, incl_zero={"g_kat" : ["prt"]}, no_pref={"g_kat" : ["prt"]}, no_zero={"g_kat" : ["prs"]}))
	write_tex("lemma_temp_prs_only", lemma_pivot(df, incl_pref={"tempus" : ["prs"]}, incl_zero={"tempus" : ["prt"]}, no_pref={"tempus" : ["prt"]}, no_zero={"tempus" : ["prs"]}))

	
	Aelf_df = df[~(df["g_kat"]=="perf")].copy()
	Aelf_df.loc[:,"doc"] = Aelf_df.loc[:,"doc"].apply(lambda x: "Ælfric" if x in ["Letters", "Prefaces", "Catholic Homilies"] else x)
	
	write_tex("lemma_Or_ga_Aelf_0", lemma_pivot(Aelf_df, incl_pref={"doc" : ["Orosius"]}, incl_zero={"doc" : ["Ælfric"]}, no_pref={"doc" : ["Ælfric"]}))
	write_tex("lemma_Aelf_ga_Or_0", lemma_pivot(Aelf_df, incl_pref={"doc" : ["Ælfric"]}, incl_zero={"doc" : ["Orosius"]}, no_pref={"doc" : ["Orosius"]}))
	
	inf_df = Aelf_df[Aelf_df["gram"]=="inf."]
	write_tex("lemma_willan_ga_sculan_0", lemma_pivot(inf_df, incl_pref={"rektion" : ["willan"]}, incl_zero={"rektion" : ["sculan"]}, no_pref={"rektion" : ["sculan"]}))
	write_tex("lemma_sculan_ga_willan_0", lemma_pivot(inf_df, incl_pref={"rektion" : ["sculan"]}, incl_zero={"rektion" : ["willan"]}, no_pref={"rektion" : ["willan"]}))
	
if any([opt == "-r" for opt,arg in opts]):
	read()
else: 
	read_from_csv()
	
for opt,arg in opts:
	if opt == "-p":
		computation_heavy()
	if opt == "-w":
		write()
	if opt == "--problem":
		problemstellen()
		interessant()