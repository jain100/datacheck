import os
from bigquery.client import BigQueryClient
from django.http import HttpResponse,HttpResponseRedirect
from django.core.files.storage import FileSystemStorage,default_storage
from django.shortcuts import render,redirect
from bigquery import get_client
from django.conf import settings
from dataapp_first.forms import DocumentForm,UrlForm
from dataapp_first.models import Document, SavedGraph
from datacheck.settings import BASE_DIR
import pandas as pd
import json
from bs4 import BeautifulSoup
import datetime
from django.views.decorators.csrf import csrf_exempt


client_dict={} #client dictionary for storing client objects


def html_to_list(table_html):
    """
    :desc: Converts the input html table to a 2D list that
           can be given as a input to the print_table function
    :param: `table_html` HTML text contaning <table> tag
    """
    if not table_html:
        return []

    soup = BeautifulSoup(table_html, 'html.parser')
    rows = soup.find('table').find_all('tr')
    th_tags = rows[0].find_all('th')
    headings = [[row.text.strip() for row in th_tags]]
    headings[0] = [x.upper() for x in headings[0]]
    data_rows = headings + [[data.text.strip() for data in row.find_all('td')] for row in rows[1:]]
    index = []
    # print(data_rows[0].index('DAY'),data_rows[0].index('MONTH'),data_rows[0].index('YEAR'))
    print(data_rows[0])
    data_rows[0].pop(0)
    index.append(data_rows[0].index('DAY'))
    index.append(data_rows[0].index('MONTH'))
    index.append(data_rows[0].index('YEAR'))
    print(index)
    for data_row in data_rows:
        date = data_row[index[2]] + '-' + data_row[index[1]] + '-' + data_row[index[0]]
        data_row.pop(index[1])
        data_row.pop(index[0])
        data_row.pop()
        data_row.append(date)
    print(data_rows[0])
    return data_rows

def takeSecond(elem):
    return elem[1]

#BIGQUERY HANDLING STARTS

def root(request):
    request.session.set_expiry(0)
    query_string = None #initially query string is none
    if request.session.has_key('client') and request.method == 'POST': #to check if client is signed in and then querying
        query_string=request.POST.get('query', 'empty')
        results = compute_query(query_string, request.session.get('client')) # returns results in form of html table
        data_rows = html_to_list(results)
        all_results = []
        table_x = []
        table_y = []
        title = ''
        time = []
        for i in range (0,len(data_rows[0])-1):
            title = data_rows[0][i]
            for data_row in data_rows[1:]:
                table_x.append((str(data_row[len(data_row)-1])))
                table_y.append(float(data_row[i]))
                if i == 0:
                    time.append(datetime.datetime.strptime(((str(data_row[len(data_row)-1]))), '%Y-%m-%d'))
            all_results.append([title,table_x,table_y])
        temp = []
        for i in range(0,len(data_rows[0])-1):
            all_results[i][1],temp = (list(t) for t in zip(*sorted(zip(all_results[i][1],time),key=takeSecond)))
            all_results[i][2],temp = (list(t) for t in zip(*sorted(zip(all_results[i][2],time),key=takeSecond)))
        request.session['all_results'] = all_results
        return render(request, 'index.html',{'results': all_results, 'connected':True})

    elif request.session.has_key('client') and request.method == 'GET': #AFTER SIGNING IN WHEN USER IS FIRST DIRECTED TO ROOT
        all_results=request.session.get('all_results', 'null')
        if all_results != 'null':
            return render(request, 'index.html',{'results': all_results, 'connected':True})
        else:
            return render(request, 'index.html',{'connected':True})
    #TO SHOW THE CONNECTED BUTTON ON TEMPLATE
    else:
        return render(request, 'index.html',{'connected':False})# WHEN USER FIRST TIME VISIT THE PAGE

def charting(request):
    documents = Document.objects.all()
    connected = False
    if request.session.has_key('client'):
        connected = True
        # for doc in documents:
        #     destination = settings.MEDIA_ROOT
        #     if not os.path.exists(destination + '/' + doc.docfile.name):
        #         print(destination + '/' + doc.docfile.name)
        #         doc.delete()
    return render(request, 'charting.html', {'documents': documents,'connected':connected})

def staging(request):
    savedGraphs = SavedGraph.objects.all()
    connected = False
    if request.session.has_key('client'):
        connected = True
    return render(request,'staging.html',{'connected':connected, 'savedGraphs':savedGraphs}) #for reporting



def fileupload(request):
    #THIS FUNCTION IS USED TO TAKE PRIVATE KEY FILE FROM USER AND AUTHENTICATE THAT USER
    if request.method == 'POST':
        myfile = request.FILES['creds']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        #uploaded_file_url = fs.url(filename)
        request=authenticate(request,filename) # this adds client information in the session object (client_file_path and client id)

        if request.session.has_key('client'): #to check if client is authenticated or signedin
            request.session.set_expiry(0) #this will expire client session if browser is closed
            return redirect('root')

        else:
            return render(request,'upload.html',{'status':False}) #this will show invalid credentials if client not authenticated

    else:
        return render(request, 'upload.html') #this is when first time client visit upload file page


def authenticate(request,filename):
    client = None
    f_path = os.path.join(BASE_DIR, 'media')
    fin_path = os.path.join(f_path, filename) #this is the actual path of client file
    try:
        json_key = fin_path #providing name to client file
        client = get_client(json_key_file=json_key, readonly=True) #this provides client object if client file is valid
        os.remove(json_key) #deleting json file from media directory as client object is saved in client_dict
        print(type(client))
        #request.session['clientfile']=json_key #client file path or json file path
        request.session['client']=id(client)#id of that client
        client_dict[request.session.get('client')]=client
        return request
    except Exception as e: #if client is not authenticated
        print(e)
        os.remove(fin_path)
        request.authenticated = False
        request.client=None
        return request


def compute_query(query_string, clientid): #parameters : query string and client id
    client=client_dict[clientid] #getting corresponding client object
    job_id, _results = client.query(query_string)
    results = client.get_query_rows(job_id) #getting results of query
    resultsdf = pd.DataFrame(results) #converting results to dataframe
    csvpath = os.path.join(BASE_DIR, 'static','dataset.csv')
    resultsdf.to_csv(csvpath) #writing query results to dataset.csv
    return resultsdf.to_html() #converting dataframe to html and returning

def logout(request): #logsout user ,expires session ,delete client object from data dictionary
    print(client_dict)
    del client_dict[request.session.get('client')]
    request.session.flush()
    return redirect('root')


#BIGQUERY HANDLING ENDS


#CSV FILE HANDLING STARTS

def csvupload(request): # for uploading csv file
    # Handle file upload
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            newdoc = Document(docfile=request.FILES['docfile'])
            newdoc.save()

            # Redirect to the document list after POST
            documents = Document.objects.all()
            return render(request, 'charting.html', {'documents': documents})
    else:
        form = DocumentForm()  # A empty, unbound form

    # Load documents for the list page
    documents = Document.objects.all()
    return render(request, 'uploadcsv.html', {'documents': documents, 'form': form})


def docaccess(request):
    url = ""
    if request.method == 'POST':
        form = UrlForm(request.POST)
        if form.is_valid():
            print (form.cleaned_data['url'])
            url = form.cleaned_data['url']
            file = default_storage.open(url, 'rb')

            print(settings.BASE_DIR)
            name=url.split('/')
            path = os.path.join(settings.BASE_DIR, 'static', 'dataset.'+name[len(name)-1])
            f = open(path, "w+b")
            f.truncate()
            f.write(file.read())
            f.close()

            request.session['working_dataset'] = 'dataset.'+name[len(name)-1]
            #print (file.read())
            documents = Document.objects.all()
            return redirect('charting')


def saveChartingGraph(request):
    if request.method == 'POST':
        savedGraphs = SavedGraph.objects.all()
        graphTopPos = 0
        graphLeftPos = 0
        lastGraphHeight = 0
        lastGraphLeft = 0
        for graph in savedGraphs:
            graphTopPos = float(graph.graphTop)
            lastGraphLeft = float(graph.graphLeft)
            lastGraphHeight = float(graph.graphHeight)
            if(graph.graphDataset == request.POST['chartDataset'] and
            graph.graphType == request.POST['chartType'] and
            graph.graphXAxisVar == request.POST['chartXAxisVar'] and
            graph.graphYAxisVar == request.POST['chartYAxisVar'] and
            graph.graphOp == request.POST['chartOp'] and
            graph.graphHist == request.POST['chartHist']):
                graph.graphTitle = request.POST['chartTitleSave']
                graph.save()
                graph.graphXAxisLabel = request.POST['chartXAxisLabel']
                graph.save()
                graph.graphYAxisLabel = request.POST['chartYAxisLabel']
                graph.save()
                return redirect('charting')

        if(int(SavedGraph.objects.count()) %2 == 1 and lastGraphLeft <= 100):
            graphLeftPos = 500
        elif(int(SavedGraph.objects.count()) == 0):
            graphTopPos += lastGraphHeight
        else:
            graphTopPos += lastGraphHeight
            graphTopPos += 30

        newGraph = SavedGraph(graphDataset=request.POST['chartDataset'],
                                graphType=request.POST['chartType'],
                                graphTitle=request.POST['chartTitleSave'],
                                graphXAxisLabel=request.POST['chartXAxisLabel'],
                                graphYAxisLabel=request.POST['chartYAxisLabel'],
                                graphXAxisVar=request.POST['chartXAxisVar'],
                                graphYAxisVar=request.POST['chartYAxisVar'],
                                graphOp=request.POST['chartOp'],
                                graphHist=request.POST['chartHist'],
                                graphHeight="400",
                                graphWidth="450",
                                graphLeft=str(graphLeftPos),
                                graphTop=str(graphTopPos),)
        newGraph.save()
    return redirect('charting')

def deleteChartingGraph(request):
    if request.method == 'POST':
        newGraph = SavedGraph.objects.all()
        i=0
        for n in newGraph:
            if(i== int(request.POST['savedChartIndex'])):
                print(n)
                n.delete()
            i+=1
    return redirect('staging')


@csrf_exempt
def saveGraphStateStaging(request):
    if request.method == 'POST':
        newGraph = SavedGraph.objects.all()
        i=0
        arr = request.POST['savedGraphAttributes'].split(",")
        for n in newGraph:
            if(arr[i].split(" ")[0]):
                n.graphWidth = arr[i].split(" ")[0]
                n.save()
            
            if(arr[i].split(" ")[1]):
                n.graphHeight = arr[i].split(" ")[1]
                n.save()
            
            i+=1
    return redirect('staging')


@csrf_exempt
def saveGraphPositionStaging(request):
    if request.method == 'POST':
        newGraph = SavedGraph.objects.all()
        i=0
        arr = request.POST['savedGraphPosition'].split(",")
        index = request.POST['index']
        print(index)
        for n in newGraph:
            if i==int(index):
                if(arr[i].split(" ")[0]):
                    n.graphLeft = str(float(arr[i].split(" ")[0])-190)
                    n.save()
            
                if(arr[i].split(" ")[1]):
                    n.graphTop = str(float(arr[i].split(" ")[1])-150)
                    n.save()
                print(arr[i].split(" ")[0] + " " + arr[i].split(" ")[1])
            i+=1
    return redirect('staging')