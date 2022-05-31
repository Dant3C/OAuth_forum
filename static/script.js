$(document).ready(function() {
	let length = $(".card").length; //Adjust this to whatever the posts are displayed in
	for(let i = 1; i <= length; i++) {
		$("#rButton"+i).click(function() {
			showReply(i);
			$("#rButton"+i).text(function(i, text){
				return text === "Reply" ? "Cancel" : "Reply";
			})
		});
	}
	
	function showReply(num) {
		$('#reply' + num).toggle();
	}
});