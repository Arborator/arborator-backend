import re, os


repoint = re.compile(r'(?<![0-9A-ZÀÈÌÒÙÁÉÍÓÚÝÂÊÎÔÛÄËÏÖÜÃÑÕÆÅÐÇØ])([.。]+)')
repointEnd = re.compile(r'([.。]+)$')
reponctWithNum = re.compile(r'(?<![0-9])(\s*[;:,!\(\)§"]+)')
# rehyph = re.compile(r'(\s*[\/]+)')  # \- pas de segmentation des traits d'union
revirer = re.compile(r'[`]+')
redoublespace = re.compile(r'\s+', re.U)
reparenth = re.compile(r'\([ \w]*\)', re.U)

treg = re.compile(r'^\d+\t(.+?)\t.*AlignBegin=(\d+).*AlignEnd=(\d+)')

def preparetokenize(text):
	text = text.strip()
	text = text.replace("’", "'")
	text = revirer.sub(r" ", text)
	text = repointEnd.sub(r" \1 ", text)
	text = repoint.sub(r" \1 ", text)
	text = reponctWithNum.sub(r" \1 ", text)
	#text=rehyph.sub(r"\1 ",text)
	return text

def intervals2conll(intervals, outname, soundfile):
	"""
	produces an empty conll text that contains only tokens and AlignBegin and AlignEnd
	from intervals (a list of triples xmin, xmax, text)
	"""
	allconll = "" 
	try: basename = os.path.basename(outname)
	except: basename = outname
	scount=1
	for xmin, xmax, sentence in intervals:
		text = " ".join(sentence)
		if not text.strip(): continue
		conll = "# sent_id = "+basename+"__"+str(scount)+'\n'
		conll += "# text = "+text+'\n'
		conll += "# sound_url = "+soundfile+'\n'
		#conll += "# minmax = "+xmin+" "+xmax+'\n'
		
		text=preparetokenize(text)
		text=redoublespace.sub(" ",text)
		text=reparenth.sub(" ",text).strip()
		text=text.replace("aujourd' hui","aujourd'hui")
		text=text.replace("quelqu' un","quelqu'un")
		toks=text.split()
		realtoks = [t for t in toks if re.search(r'\w',t)]
		if not realtoks: continue
		msecs = (float(xmax)-float(xmin))/len(realtoks)
		start = float(xmin)
		for i,t in enumerate(toks):
			if re.search(r'\w',t): end = start+msecs
			conll += '\t'.join([str(i+1),t,t,'_','_','_','_','_','_','AlignBegin={xmin}|AlignEnd={xmax}'.format(xmin=round(start),xmax=round(end))])+'\n'
			start=end
		scount+=1
		allconll += conll+'\n'
	return allconll

def intervals2conllfile(intervals, outname, soundfile):
	open(outname, 'w').write(intervals2conll(intervals, outname, soundfile))
	

def newtranscription(inconll, transcription, samplename, soundfile):
	"""
	uses the time delimitations of inconll to construct a new conll text
	inconll: name of conll file to take as the base
	transcription: list of texts
	the number of trees in inconll has to be equal to the number of transcription
	samplename: used for constructing the sent_id (sent_id = samplename+"__"+ sentence number)
	soundfile: what is supposed to appear behind sound_url = 
	"""
	conlls = open(inconll).read().strip().split('\n\n')
	if type(transcription) != list:
		raise Exception

	if len(conlls) != len(transcription): 
		raise Exception
	
	intervals = []
	for co, tr in zip(conlls,transcription):
		sent = []
		for li in co.strip().split('\n'):
			if li and li[0] != '#':
				m = treg.search(li)
				w = m.group(1)
				sent += [(w, int(m.group(2)), int(m.group(3)))]
				
		intervals += [(sent[0][1], sent[-1][2], tr)]
	return intervals2conll(intervals, samplename, soundfile)


def test_newtranscription():
	inconll ="corpussamples/Radya_Laichour/Radya_Laichour.intervals.conll"
	nrsent = len(open(inconll).read().strip().split('\n\n'))
	transcription = ['blah blah blah' for i in range(nrsent)]
	print(newtranscription(inconll, transcription, 'testsample', 'https://test.mp3'))


if __name__ == "__main__":
	test_newtranscription()
