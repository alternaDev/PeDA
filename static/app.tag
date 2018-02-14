<app>
  <nav><a each={ data } href="#{ id }">{ title }</a></nav>
  <article>
    <h1>{ currentData ? currentData[0].name : 'Persons' }</h1>
    <ul>
	<li each={ name in names }><a href={"#" + name}>{name}</a></li>
    </ul>
    <div each={ currentData }>
      {moment(new Date(time)).fromNow()}: {status} <img src={path} alt={new Date(time)} width=100/>
    </div>
  </article>
  <script>
    var self = this
    self.names = []
    self.currentData = null;
    fetch('/names').then(function(r){return r.json()}).then(function(json) {
        self.names = json.filter(function(i) {return i;});
        self.update()
    });
    route(function(id) {
      if(id) {
        fetch('/data/' + id).then(function(r){return r.json()}).then(function(d) {
          self.currentData = d;
	  self.currentData.sort(function(a, b) {
	    return new Date(b.time) - new Date(a.time); 
	  });
          self.update()
        });
      }
    })
  </script>
  <style>
  </style>
</app>
