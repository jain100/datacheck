import os
from bigquery.client import BigQueryClient
from django.http import HttpResponse,HttpResponseRedirect
from django.core.files.storage import FileSystemStorage,default_storage
from django.shortcuts import render,redirect
from bigquery import get_client
from django.conf import settings
from dataapp_first.forms import DocumentForm,UrlForm
from dataapp_first.models import Document
from datacheck.settings import BASE_DIR
import pandas as pd

client_dict={} #client dictionary for storing client objects

#BIGQUERY HANDLING STARTS

def root(request):
    request.session.set_expiry(0)
    query_string = None #initially query string is none
    if request.session.has_key('client') and request.method == 'POST': #to check if client is signed in and then querying
        query_string=request.POST.get('query', 'empty')
        #print(query_string) # for testing
        #print('in post  ', request.session['client']) #for testing
        results = compute_query(query_string,request.session.get('client')) # returns results in form of html table
        print(request.session.get('client'))
        return render(request, 'results.html', {'data':results})

    elif request.session.has_key('client') and request.method == 'GET': #AFTER SIGNING IN WHEN USER IS FIRST DIRECTED TO ROOT
        print(request.session.get('client') , 'or empty')
        return render(request,'index.html',{'connected':True})#TO SHOW THE CONNECTED BUTTON ON TEMPLATE
    else:
        #print('in get ')
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

# def charting(request):
#     connected=False
#     if request.session.has_key('client'):
#         connected=True
#     return render(request,'charting.html',{'connected':connected}) #for charting

def staging(request):
    connected = False
    if request.session.has_key('client'):
        connected = True
    return render(request,'staging.html',{'connected':connected}) #for reporting
#
#


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


def compute_query(query_string,clientid): #parameters : query string and client id
    client=client_dict[clientid] #getting corresponding client object
    job_id, _results = client.query(query_string)
    results = client.get_query_rows(job_id) #getting results of query
    resultsdf = pd.DataFrame(results) #converting results to dataframe
    csvpath = os.path.join(BASE_DIR, 'static','dataset.csv')
    resultsdf.to_csv(csvpath) #writing query results to dataset.csv
    return resultsdf.to_html() #converting dataframe to html and returning

def logout(request): #logsout user ,expires session ,delete client object from data dictionary
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

            path = os.path.join(settings.BASE_DIR, 'static', 'dataset.csv')
            f = open(path, "w+b")
            f.truncate()
            f.write(file.read())
            f.close()

            #print (file.read())
            documents = Document.objects.all()
            return redirect('charting')