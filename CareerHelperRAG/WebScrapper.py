import requests
from bs4 import BeautifulSoup

# Define the output file path
output_file = 'scuola_di_studi_superiori_ferdinando_rossi.txt'

# Send a GET request to the webpage
url = 'https://www.unito.it/didattica/offerta-formativa/scuola-di-studi-superiori-ferdinando-rossi'
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Decode the content using the specified encoding
    response.encoding = 'utf-8'  # Specify the encoding
    # Parse the HTML content of the webpage
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the elements containing the data you want to scrape
    #cores = soup.find_all('section', id='corpo-pagina')
    cores = soup.find_all('div', class_='ds-1col node node-pagina-area0 view-mode-full clearfix')
    
    # Open the output file in write mode
    with open(output_file, 'w', encoding='utf-8') as f:  # Specify encoding for writing
        # Iterate over each core element
        for core in cores:
            # Remove newline characters and use a single space between rows
            text_without_newlines = ' '.join(core.text.strip().split())
            # Write the modified text to the output file
            f.write(text_without_newlines + '\n')

    print("Data extracted and saved to", output_file)
else:
    print('Failed to retrieve the webpage')
