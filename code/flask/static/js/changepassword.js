$(function() {
    console.log( "ready!" );


        $("#submit-button").click(function(){
            //event.preventDefault();
            var confirmPassword = document.getElementById('confirm_password').value;
            var changePassword = document.getElementById('changepassword').value;
            //alert("PASS 1 : " + confirmPassword + " || pass 2 : " + changePassword);

            
            console.log("Button clicked");
            if(confirmPassword == changePassword) {
                //alert("Passwords match!")
                return true;
            }
            else {
                alert("Passwords must match!");
                return false;
            }
          });

      
});