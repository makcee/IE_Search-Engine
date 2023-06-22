import json
import hazm
import re

def getDict(docs_path):
    # we use python dictionary data structure because
    # we have key-value pairs and duplicates shouldn't be allowed 
    # keys are numbers (doc ids in string) and 
    # values are again dictionaries ({'title': '...', 'content': '...',})
    dictionary = {}
    file = open(docs_path, "r")
    file_contents = file.read() # a string content
    file.close()
    parsed_json = json.loads(file_contents) # valid dictionary
    for id in parsed_json.keys():
        dictionary[id] = {} # nested dictionary
    id = 0
    for news in parsed_json.values():
        dictionary[str(id)]['title'] = news['title']
        dictionary[str(id)]['content'] = news['content']
        dictionary[str(id)]['url'] = news['url']
        id += 1
    return dictionary

def preprocess_news(nested_dictionary):
    nest_len = len(nested_dictionary)
    for id in range(0, nest_len):
        nested_dictionary[str(id)]['content'] = hazm.Normalizer().normalize(nested_dictionary[str(id)]['content'])
        nested_dictionary[str(id)]['content'] = hazm.word_tokenize(nested_dictionary[str(id)]['content'])
        for token in nested_dictionary[str(id)]['content']:
            if (token in hazm.stopwords_list()):
                nested_dictionary[str(id)]['content'].remove(token)
        t_index = 0
        for token in nested_dictionary[str(id)]['content']:
            nested_dictionary[str(id)]['content'][t_index] = hazm.Stemmer().stem(token)
            t_index += 1
    return nested_dictionary

def createPositionalIndex(preprocessed_dictionary):
    posIndex = {}
    for id, news in preprocessed_dictionary.items():
        for counter in range(0, len(news['content'])):
            term = news['content'][counter]
            if term not in posIndex:
                posIndex[term] = {}
                posIndex[term]['termFreq'] = 1
                posIndex[term]['posts'] = {}
                posIndex[term]['posts'][id] = {}
                posIndex[term]['posts'][id]['docFreq'] = 1
                posIndex[term]['posts'][id]['pos'] = [counter]
            else:
                posIndex[term]['termFreq'] += 1
                # the term occures more than once in the document
                if id in posIndex[term]['posts']:
                    posIndex[term]['posts'][id]['docFreq'] += 1
                    posIndex[term]['posts'][id]['pos'].append(counter)
                # the term occures once more in another document
                else:
                    posIndex[term]['posts'][id] = {}
                    posIndex[term]['posts'][id]['docFreq'] = 1
                    posIndex[term]['posts'][id]['pos'] = [counter]
    
    return posIndex

def query(index, preprocessedDict, queryText):
    negatedTerms = re.findall(r'\!(\w+)', queryText)
    phrasalTerms = re.findall(r'"([^"]*)"', queryText)
    otherTerms = re.sub(r'\!(\w+)|"([^"]*)"', '', queryText).split()
    
    toBeRemoved = []
    if len(negatedTerms) > 0:
        counter = 0
        for term in negatedTerms:
            if term in hazm.stopwords_list(): 
                toBeRemoved.append(term)
                counter += 1
                continue
            negatedTerms[counter] = hazm.Stemmer().stem(term)
            counter += 1
        for term in toBeRemoved:
            negatedTerms.remove(term)
    
    negated_index = {}
    negated_posts = {}
    negated_idLists = {}
    if len(negatedTerms) > 0:
        for term in negatedTerms:
            negated_index[term] = index[term]
            negated_posts[term] = negated_index[term]['posts']
            negated_idLists[term] = []
            for id in negated_posts[term].keys():
                negated_idLists[term].append(id)
        negatedComplete = []
        for term in negated_idLists.keys():
            for id in negated_idLists[term]:
                negatedComplete.append(id)
        if len(otherTerms) == 0 and len(phrasalTerms) == 0:
            notNegated = {}
            for id in preprocessedDict.keys():
                if id not in negatedComplete:
                    notNegated[id] = preprocessedDict[id]
            limit = 5
            for id in notNegated.keys():
                print("ID: " + id)
                print("Title: " + preprocessedDict[id]['title'])
                print("URL: " + preprocessedDict[id]['url'])
                limit -= 1
                if limit == 0:
                    break
            return
    

    if len(phrasalTerms) > 0:
        phrasals = []
        for seq in phrasalTerms:
            norm = hazm.Normalizer().normalize(seq)
            normTaken = hazm.word_tokenize(norm)
        counter = 0
        for term in normTaken:
            normTaken[counter] = hazm.Stemmer().stem(term)
            counter += 1

    ph_index = {}
    ph_posts = {}
    ph_idLists = {}
    interID = []
    if len(phrasalTerms) > 0:
        for term in normTaken:
            ph_index[term] = index[term]
            ph_posts[term] = ph_index[term]['posts']
            ph_idLists[term] = []
            for id in ph_posts[term].keys():
                ph_idLists[term].append(id)
        initial = 0
        interPh = []
        for ids in ph_idLists.values():
            if initial == 0:
                interPh = [value for value in ids if value in ids]
                initial += 1
            else:
                interPh = [value for value in interPh if value in ids]
        posList = {}
        initial = 0
        for id in interPh:
            for term in ph_posts:
                if initial == 0:
                    posList[term] = {}
                posList[term][id] = ph_posts[term][id]['pos']
            initial += 1
        for id in interPh:
            counter = 0
            for term in posList:
                posListIndex = 0
                for position in posList[term][id]:
                    posList[term][id][posListIndex] -= counter
                    posListIndex += 1
                counter += 1
        
        interPos = []
        termList = list(posList.keys())
        for id in interPh:
            initial = 0
            for i in range(0, len(posList)):
                positions = posList[termList[i]][id]
                if initial == 0:
                    interPos = [value for value in positions if value in positions]
                    initial += 1
                else:
                    interPos = [value for value in interPos if value in positions]
            if len(interPos) > 0:
                interID.append(id)
        
        if len(interID) > 0 and len(otherTerms) == 0 and len(negatedTerms) > 0 :
            phNegated = []
            for id in interID:
                if id not in negatedComplete:
                    phNegated.append(id)
            ranked_intersections = {}
            initial = 0
            for term in ph_posts:
                for id in phNegated:
                    if initial == 0:
                        ranked_intersections[id] = ph_posts[term][id]['docFreq']
                    else:
                        ranked_intersections[id] += ph_posts[term][id]['docFreq']
                initial += 1
            sorted_ranked_intersections = dict(sorted(ranked_intersections.items(), key=lambda x: x[1], reverse=True))
            limit = 5
            for id, freq in sorted_ranked_intersections.items():
                print("ID: " + id)
                print("Total Frequency: " + str(freq))
                print("Title: " + preprocessedDict[id]['title'])
                print("URL: " + preprocessedDict[id]['url'])
                limit -= 1
                if limit == 0:
                    break
            return

        if len(interID) > 0 and len(otherTerms) == 0 and len(negatedTerms) == 0 :
            ranked_intersections = {}
            initial = 0
            for term in ph_posts:
                for id in interID:
                    if initial == 0:
                        ranked_intersections[id] = ph_posts[term][id]['docFreq']
                    else:
                        ranked_intersections[id] += ph_posts[term][id]['docFreq']
                initial += 1
            sorted_ranked_intersections = dict(sorted(ranked_intersections.items(), key=lambda x: x[1], reverse=True))
            limit = 5
            for id, freq in sorted_ranked_intersections.items():
                print("ID: " + id)
                print("Total Frequency: " + str(freq))
                print("Title: " + preprocessedDict[id]['title'])
                print("URL: " + preprocessedDict[id]['url'])
                limit -= 1
                if limit == 0:
                    break
            return


    toBeRemoved = []
    if len(otherTerms) > 0:
        counter = 0
        for term in otherTerms:
            if term in hazm.stopwords_list(): 
                toBeRemoved.append(term)
                counter += 1
                continue
            otherTerms[counter] = hazm.Stemmer().stem(term)
            counter += 1
        for term in toBeRemoved:
            otherTerms.remove(term)
    
    other_index = {}
    other_posts = {}
    other_idLists = {}
    existance = False
    if len(otherTerms) > 0:
        for term in otherTerms:
            if term not in index.keys():
                continue
            existance = True
            other_index[term] = index[term]
            other_posts[term] = other_index[term]['posts']
            other_idLists[term] = []
            for id in other_posts[term].keys():
                other_idLists[term].append(id)
        if existance == False:
            print("NO RESULTS!!!")
            return
        initial = 0
        intersections = []
        for ids in other_idLists.values():
            if initial == 0:
                intersections = [value for value in ids if value in ids]
                initial += 1
            else:
                intersections = [value for value in intersections if value in ids]
        
        interRemove = []
        for term in negated_posts:
            for id in intersections:
                if id in negated_idLists[term]:
                    interRemove.append(id)
        for id in interRemove:
            if id in intersections:
                intersections.remove(id)
        
        tempInter = []
        for id in interID:
            if id in intersections:
                tempInter.append(id)
        if len(interID) > 0:
            intersections = tempInter
        if len(interID) == 0 and len(phrasalTerms) > 0:
            print("NO RESULTS!!!")
            return
            
        ranked_intersections = {}
        initial = 0
        for term in other_posts:
            for id in intersections:
                if initial == 0:
                    ranked_intersections[id] = other_posts[term][id]['docFreq']
                else:
                    ranked_intersections[id] += other_posts[term][id]['docFreq']
            initial += 1
        sorted_ranked_intersections = dict(sorted(ranked_intersections.items(), key=lambda x: x[1], reverse=True))
        limit = 5
        for id, freq in sorted_ranked_intersections.items():
            print("ID: " + id)
            print("Total Frequency: " + str(freq))
            print("Title: " + preprocessedDict[id]['title'])
            print("URL: " + preprocessedDict[id]['url'])
            limit -= 1
            if limit == 0:
                break
            

if __name__ == '__main__':
    
    """
    # myDictionary = getDict('IR_data_news_12k.json')
    # preprocessed_dictionary = preprocess_news(myDictionary)
    SAVE THE PREPROCESSED FILE
    json_obj = json.dumps(preprocessed_dictionary)
    file = open("preprocessed.json","w")
    file.write(json_obj)
    file.close()
    """
    file = open("preprocessed.json", "r")
    file_contents = file.read() # a string content
    file.close()
    preprocessedDict = json.loads(file_contents) # valid dictionary
    
    """
    positionalIndex = createPositionalIndex(preprocessedDict)
    SAVE THE POSITIONAL iNDEX
    json_obj = json.dumps(positionalIndex)
    file = open("posIndex.json","w")
    file.write(json_obj)
    file.close()
    """
    file = open("posIndex.json", "r")
    file_contents = file.read() # a string content
    file.close()
    positionalIndex = json.loads(file_contents)

    #testDict = query(positionalIndex, preprocessedDict, 'تحریم‌های آمریکا علیه ایران')
    #testDict = query(positionalIndex, preprocessedDict, 'تحریم‌های آمریکا !ایران')
    #testDict = query(positionalIndex, preprocessedDict, '"کنگره ضدتروریست"')
    #testDict = query(positionalIndex, preprocessedDict, '"تحریم هسته‌ای" آمریکا !ایران')
    #testDict = query(positionalIndex, preprocessedDict, 'اورشلیم !صهیونیست')

    testDict = query(positionalIndex, preprocessedDict, '"دانشگاه صنعتی" !تهران')

    #testDict = query(positionalIndex, preprocessedDict, '"صدور دستور"')
    #testDict = query(positionalIndex, preprocessedDict, '"صدور دستور" ایران')


