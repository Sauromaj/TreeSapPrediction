
function checkBox(checkbox){
    if ( checkbox.checked){
        revealYield();
    }
    else{
        hideYield();
    }
}

function revealYield(){
    console.log("Shown yield!")
    document.getElementById("giveYield").innerHTML ="<br><input type='text' id='trees' name ='trees' placeholder='Enter your number of tree taps' style = 'font-family: Poppins; font-size: 16px;' size= '70;'><script>document.getElementById('search').addEventListener('click', async () => {const yieldInput = document.getElementById('yield').value;if (!yieldInput) {alert('Please enter a yield.');return;}try {const response = await fetch('/api/freeze-thaw', {method: 'POST',headers: {'Content-Type': 'application/json',},body: JSON.stringify({ location: yieldInput }),});if (!response.ok) {throw new Error(`Server error: ${response.status}`);}const data = await response.json();console.log('Response from backend:', data);alert('Data successfully sent!');} catch (error) {console.error('Error sending data:', error);alert('Failed to send data. Check the console for details.');}});</script>" 
}

function hideYield(){
    console.log("Hid yield!")
    document.getElementById("giveYield").innerHTML ="" 
}
