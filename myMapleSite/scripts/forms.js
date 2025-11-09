let textLocation;
let valueNumber

document.getElementById("search").onclick = function(){
    textLocation = document.getElementById("location").value;
    console.log(textLocation);

    showInformation();
    showResults()
    showEstimate()
    showSMS();
}

function showInformation(){
    console.log("Shown map!")
    document.getElementById("map").innerHTML = "<br><iframe src=\"https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d45178.71641629543!2d-79.81629439999999!3d43.7157888!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e1!3m2!1sen!2sca!4v1762672110238!5m2!1sen!2sca\" width='600' height='450' style='border:0;'' allowfullscreen=' ' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>"
}

function showResults(){
    console.log("Shown results!")
    document.getElementById("results").innerHTML ="<br><h2>YOUR MAPLE TAP INFORMATION</h2><h3 style='margin-right:20%; margin-left: 20%;color: #0C0C0C;'>START DATE: Feb 22nd 2026<br>END DATE: Mar. 1st 2026<br>IDEAL TAP DATE: Feb 29th 2026</h3>"
}

function showEstimate() {
    if(document.getElementById("yield").checked){
        document.getElementById("results").innerHTML ="<br><h2>YOUR MAPLE TAP INFORMATION</h2><h3 style='margin-right:20%; margin-left: 20%;color: #0C0C0C;'>START DATE: Feb 22nd 2026<br>END DATE: Mar. 1st 2026<br>IDEAL TAP DATE: Feb 29th 2026<br>ESTIMATED YIELD:  45gal</h3>"
    } else{
        console.log('ugh')

    }
}


function showSMS(){
    console.log("I am tired")
    // document.getElementById("sms").innerHTML ="<br><h3 style='margin-right:20%; margin-left: 20%;color: #0C0C0C;'>Want to review SMS updates? Enter your phone number</h3><input type='text' id='trees' name ='trees' placeholder='###-###-####' style = 'font-family: Poppins; font-size: 16px;' size= '40;'><br><br> <button type='submit' id = 'numberSubmit' style='font-family: Poppins; font-size: 18px;'>Enter</button>"
}

// document.getElementById("numberSubmit").onclick = function(){
//     textLocation = document.getElementById("numberSubmit").value;
//     console.log(valueNumber);
// }

// function hideNumber(){
//     document.getElementById("sms").innerHTML ="<br><h3 style='margin-right:20%; margin-left: 20%;color: #0C0C0C;'>Number accepted! <br> 'valueNumber'</h3>"
// }
