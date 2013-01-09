<script type="text/javascript">
$(document).ready(function() {
    $('span.timeago').timeago();
});

$('#tiles').imagesLoaded(function() {
  var options = {
    autoResize: true, 
    container: $('#timeline'),
    offset: 15,
    itemWidth: 238,
  };
  var handler = $('#tiles>li');
  handler.wookmark(options);
});
</script>
