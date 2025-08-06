const likeBtn = document.getElementById('likeBtn');
const likeCount = document.getElementById('likeCount');
const toast = document.getElementById('toast');
const nextBtn = document.getElementById('nextBtn');
const currentPost = document.getElementById('currentPost');
const loadingPost = document.getElementById('loadingPost');

let isAnimating = false;
let currentPostId = postId;

updateLikeButton();

function updateLikeButton() {
    if (isLiked) {
        likeBtn.classList.add('liked');
    } else {
        likeBtn.classList.remove('liked');
    }
    likeCount.textContent = currentLikeCount;
}

async function toggleLike() {
    if (isAnimating) return;
    
    likeBtn.disabled = true;

    try {
        const response = await fetch('/toggle_like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ postid: currentPostId })
        });

        const data = await response.json();

        if (data.success) {
            isLiked = data.liked;
            currentLikeCount = data.like_count;
            updateLikeButton();
            showToast(data.message);
        } else {
            showToast('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        showToast('Error occurred while toggling like');
    } finally {
        likeBtn.disabled = false;
    }
}

async function loadNextPost() {
    if (isAnimating) return;
    
    isAnimating = true;
    nextBtn.disabled = true;
    nextBtn.classList.add('loading');
    
    try {
        loadingPost.style.display = 'flex';
        
        currentPost.classList.add('swipe-up');
        
        await new Promise(resolve => setTimeout(resolve, 300));
        
        const response = await fetch('/api/random_post');
        const data = await response.json();
        
        if (data.success && data.post) {
            updatePostContent(data.post);
            
            loadingPost.style.display = 'none';
            
            currentPost.classList.remove('swipe-up');
            currentPost.classList.add('swipe-in');
            
            currentPost.offsetHeight;
            
            currentPost.classList.add('active');
            
            setTimeout(() => {
                currentPost.classList.remove('swipe-in', 'active');
            }, 600);
            
            showToast('New post loaded!', 'success');
        } else {
            loadingPost.style.display = 'none';
            currentPost.classList.remove('swipe-up');
            showToast('No more posts available or error loading post');
        }
    } catch (error) {
        console.error('Error loading next post:', error);
        loadingPost.style.display = 'none';
        currentPost.classList.remove('swipe-up');
        showToast('Error loading next post');
    } finally {
        isAnimating = false;
        nextBtn.disabled = false;
        nextBtn.classList.remove('loading');
    }
}

function updatePostContent(post) {
    isLiked = post.user_liked;
    currentLikeCount = post.like_count;
    currentPostId = post.postid;
    
    const username = currentPost.querySelector('.username');
    const postDate = currentPost.querySelector('.post-date');
    const postId = currentPost.querySelector('.post-id');
    const postText = currentPost.querySelector('.post-content p');
    const viewBtn = currentPost.querySelector('.view-btn');
    
    username.textContent = `@${post.username}`;
    username.href = `/account/${post.username}`;
    postDate.textContent = post.created_at;
    postId.textContent = `ID: ${post.postid}`;
    postText.innerHTML = linkify(post.posttext);
    viewBtn.href = `/post/${post.postid}`;
    
    updateLikeButton();
}

function linkify(text) {
    const urlPattern = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

function showToast(message, type = 'default') {
    toast.textContent = message;
    toast.className = 'toast';
    
    if (type === 'success') {
        toast.classList.add('success');
    }
    
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

async function refreshLikeStatus() {
    try {
        const response = await fetch(`/get_like_status/${currentPostId}`);
        const data = await response.json();

        if (data.success) {
            isLiked = data.liked;
            currentLikeCount = data.like_count;
            updateLikeButton();
        }
    } catch (error) {
        console.error('Error refreshing like status:', error);
    }
}

document.addEventListener('keydown', function(event) {
    if ((event.code === 'Space' || event.code === 'ArrowUp') && !isAnimating) {
        event.preventDefault();
        loadNextPost();
    }
    
    if (event.code === 'KeyL' && !isAnimating) {
        event.preventDefault();
        toggleLike();
    }
});

let touchStartY = 0;
let touchEndY = 0;

currentPost.addEventListener('touchstart', function(event) {
    touchStartY = event.changedTouches[0].screenY;
});

currentPost.addEventListener('touchend', function(event) {
    touchEndY = event.changedTouches[0].screenY;
    handleSwipe();
});

function handleSwipe() {
    const swipeThreshold = 50;
    const swipeDistance = touchStartY - touchEndY;
    
    if (swipeDistance > swipeThreshold && !isAnimating) {
        loadNextPost();
    }
}

refreshLikeStatus();