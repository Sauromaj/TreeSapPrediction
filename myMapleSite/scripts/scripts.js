
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
    document.getElementById("giveYield").innerHTML ="<br><input type='text' id='trees' name ='trees' placeholder='Enter your number of tree taps' style = 'font-family: Poppins; font-size: 16px;' size= '70;' >" 
}

function hideYield(){
    console.log("Hid yield!")
    document.getElementById("giveYield").innerHTML ="" 
}
