$(function() {
    console.log( "ready!" );

        $("#sign-up-button").click(function(){
            //alert("Button clicked");
            var confirmPassword = document.getElementById('confirm_password').value;
            var changePassword = document.getElementById('password').value;
            //alert("PASS 1 : " + confirmPassword + " || PASS 2 : " + changePassword);
            
            //console.log("Button clicked");
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